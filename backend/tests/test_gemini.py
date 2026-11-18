"""Provedor Gemini: o cliente da API, sem rede, e a escolha pelo `IA_PROVEDOR`.

Como no Ollama, o Google não entra aqui: o `MockTransport` do httpx2 responde
o que a API responde (eventos SSE `data: {...}` e JSON de erro).
"""

import asyncio
import json
from collections.abc import AsyncGenerator

import httpx2
import pytest
from pydantic import ValidationError

from app.core.config import GEMINI_MODELOS_PADRAO, Settings, settings
from app.ia import IAIndisponivel, MensagemIA, get_provedor_ia, get_provedor_ia_tarefas, para
from app.ia.base import DIMENSOES_EMBEDDING
from app.ia.gemini import Gemini

MENSAGENS = [
    MensagemIA("system", "Seja breve."),
    MensagemIA("user", "O que é um laço?"),
    MensagemIA("assistant", "Uma repetição."),
    MensagemIA("user", "E um for?"),
]


async def coletar(fluxo: AsyncGenerator[str]) -> list[str]:
    return [pedaco async for pedaco in fluxo]


def eventos(*pedacos: str) -> bytes:
    linhas = [
        "data: "
        + json.dumps({"candidates": [{"content": {"role": "model", "parts": [{"text": p}]}}]})
        for p in pedacos
    ]
    return ("\n\n".join(linhas) + "\n\n").encode()


def gemini(handler, *, tentativas: int = 2, raciocinio: str | None = "low") -> Gemini:
    return Gemini(
        "chave-de-teste",
        "gemini-2.5-flash",
        timeout_conexao=1,
        timeout_leitura=1,
        tentativas=tentativas,
        raciocinio=raciocinio,
        espera_entre_tentativas=0,
        transport=httpx2.MockTransport(handler),
    )


def test_transmite_os_pedacos_e_manda_o_pedido_no_formato_do_gemini() -> None:
    pedidos: list[httpx2.Request] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        pedidos.append(pedido)
        return httpx2.Response(200, content=eventos("Um laço ", "repete."))

    formato = {"type": "object", "properties": {"x": {"type": "string"}}}
    pedacos = asyncio.run(coletar(gemini(handler).gerar(MENSAGENS, max_tokens=42, formato=formato)))

    # Com `formato` (extração em JSON), a resposta chega inteira, num pedaço só.
    assert pedacos == ["Um laço repete."]
    pedido = pedidos[0]
    assert pedido.url.path.endswith("/models/gemini-2.5-flash:streamGenerateContent")
    assert pedido.url.params["alt"] == "sse"
    # A chave vai no cabeçalho, nunca na URL.
    assert pedido.headers["x-goog-api-key"] == "chave-de-teste"
    assert "key" not in pedido.url.params

    corpo = json.loads(pedido.content)
    assert corpo["systemInstruction"] == {"parts": [{"text": "Seja breve."}]}
    assert [c["role"] for c in corpo["contents"]] == ["user", "model", "user"]
    assert corpo["generationConfig"] == {
        "maxOutputTokens": 42,
        "responseMimeType": "application/json",
        "responseJsonSchema": formato,
        "thinkingConfig": {"thinkingLevel": "low"},
    }


def test_sem_raciocinio_configurado_o_campo_nao_vai() -> None:
    pedidos: list[httpx2.Request] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        pedidos.append(pedido)
        return httpx2.Response(200, content=eventos("ok"))

    asyncio.run(coletar(gemini(handler, raciocinio="").gerar(MENSAGENS, max_tokens=5)))

    assert "thinkingConfig" not in json.loads(pedidos[0].content)["generationConfig"]


def test_o_raciocinio_do_modelo_nao_vira_resposta() -> None:
    corpo = (
        "data: "
        + json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "pensando...", "thought": True}, {"text": "Oi"}]
                        }
                    }
                ]
            }
        )
        + "\n\n"
    ).encode()

    pedacos = asyncio.run(
        coletar(
            gemini(lambda _: httpx2.Response(200, content=corpo)).gerar(MENSAGENS, max_tokens=5)
        )
    )

    assert pedacos == ["Oi"]


def test_limite_da_camada_gratuita_tenta_de_novo_e_depois_desiste() -> None:
    chamadas = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal chamadas
        chamadas += 1
        return httpx2.Response(
            429,
            json={
                "error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}
            },
        )

    with pytest.raises(IAIndisponivel, match="429"):
        asyncio.run(coletar(gemini(handler, tentativas=3).gerar(MENSAGENS, max_tokens=5)))
    assert chamadas == 3


def test_429_passageiro_se_resolve_na_nova_tentativa() -> None:
    respostas = iter(
        [
            httpx2.Response(429, json={"error": {"message": "slow down"}}),
            httpx2.Response(200, content=eventos("ok")),
        ]
    )

    pedacos = asyncio.run(coletar(gemini(lambda _: next(respostas)).gerar(MENSAGENS, max_tokens=5)))

    assert pedacos == ["ok"]


def test_chave_invalida_vira_ia_indisponivel_sem_tentar_de_novo() -> None:
    chamadas = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal chamadas
        chamadas += 1
        return httpx2.Response(400, json={"error": {"message": "API key not valid"}})

    with pytest.raises(IAIndisponivel, match="API key not valid"):
        asyncio.run(coletar(gemini(handler).gerar(MENSAGENS, max_tokens=5)))
    assert chamadas == 1


def test_pedido_bloqueado_pelo_filtro_vira_ia_indisponivel() -> None:
    corpo = ("data: " + json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}) + "\n\n").encode()

    with pytest.raises(IAIndisponivel, match="SAFETY"):
        asyncio.run(
            coletar(
                gemini(lambda _: httpx2.Response(200, content=corpo)).gerar(MENSAGENS, max_tokens=5)
            )
        )


def test_embeddings_pedem_a_dimensao_do_vault_e_vem_normalizados() -> None:
    pedidos: list[httpx2.Request] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        pedidos.append(pedido)
        quantos = len(json.loads(pedido.content)["requests"])
        return httpx2.Response(
            200, json={"embeddings": [{"values": [2.0] * DIMENSOES_EMBEDDING}] * quantos}
        )

    vetores = asyncio.run(gemini(handler).embeddings(["a", "b"]))

    assert len(vetores) == 2
    assert abs(sum(v * v for v in vetores[0]) - 1) < 1e-9
    corpo = json.loads(pedidos[0].content)
    assert pedidos[0].url.path.endswith("/models/gemini-embedding-001:batchEmbedContents")
    assert {r["outputDimensionality"] for r in corpo["requests"]} == {DIMENSOES_EMBEDDING}


def test_embeddings_de_muitos_textos_vao_em_lotes_de_100() -> None:
    tamanhos: list[int] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        quantos = len(json.loads(pedido.content)["requests"])
        tamanhos.append(quantos)
        return httpx2.Response(
            200, json={"embeddings": [{"values": [1.0] * DIMENSOES_EMBEDDING}] * quantos}
        )

    vetores = asyncio.run(gemini(handler).embeddings(["t"] * 250))

    assert len(vetores) == 250
    assert tamanhos == [100, 100, 50]


def test_ia_provedor_gemini_monta_um_modelo_por_uso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ia_provedor", "gemini")
    monkeypatch.setattr(settings, "ia_reserva", "")
    monkeypatch.setattr(settings, "gemini_api_key", "chave")
    monkeypatch.setattr(settings, "gemini_modelo", "gemini-flash-lite-latest")
    monkeypatch.setattr(settings, "gemini_modelos", {"exercicios": "gemini-3.5-flash"})

    chat, tarefas = get_provedor_ia(), get_provedor_ia_tarefas()

    assert isinstance(para(chat, "chat"), Gemini)
    assert para(chat, "chat").modelo == "gemini-flash-lite-latest"
    # O do `.env` vale mais que o padrão; sem ele, o padrão do uso.
    assert para(tarefas, "exercicios").modelo == "gemini-3.5-flash"
    assert para(tarefas, "correcao").modelo == GEMINI_MODELOS_PADRAO["correcao"]
    assert para(tarefas, "ementa").timeout.read == settings.ia_timeout_leitura_tarefas


def test_gemini_sem_chave_nao_sobe_em_producao() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        Settings(
            environment="production",
            jwt_secret="s" * 40,
            fila="redis",
            ia_provedor="gemini",
            gemini_api_key="",
        )
    # Em desenvolvimento sobe: o pedido é que falha, com a mensagem da chave.
    assert Settings(ia_provedor="gemini", gemini_api_key="").ia_provedor == "gemini"


def test_sem_chave_o_pedido_vira_ia_indisponivel() -> None:
    sem_chave = Gemini("", "gemini-2.5-flash", timeout_conexao=1, timeout_leitura=1, tentativas=1)

    with pytest.raises(IAIndisponivel, match="GEMINI_API_KEY"):
        asyncio.run(coletar(sem_chave.gerar(MENSAGENS, max_tokens=5)))


def test_producao_aceita_o_gemini() -> None:
    producao = Settings(
        environment="production",
        jwt_secret="s" * 40,
        fila="redis",
        ia_provedor="gemini",
        gemini_api_key="chave",
    )
    assert producao.ia_provedor == "gemini"


def test_numero_vira_orcamento_de_tokens_dos_modelos_2_5() -> None:
    pedidos: list[httpx2.Request] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        pedidos.append(pedido)
        return httpx2.Response(200, content=eventos("ok"))

    asyncio.run(coletar(gemini(handler, raciocinio="0").gerar(MENSAGENS, max_tokens=5)))

    configuracao = json.loads(pedidos[0].content)["generationConfig"]
    assert configuracao["thinkingConfig"] == {"thinkingBudget": 0}


def test_modelo_que_recusa_o_raciocinio_e_chamado_de_novo_sem_ele() -> None:
    pedidos: list[dict] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        corpo = json.loads(pedido.content)
        pedidos.append(corpo)
        if "thinkingConfig" in corpo["generationConfig"]:
            return httpx2.Response(400, json={"error": {"message": "invalid argument"}})
        return httpx2.Response(200, content=eventos("ok"))

    pedacos = asyncio.run(
        coletar(gemini(handler, raciocinio="0", tentativas=1).gerar(MENSAGENS, max_tokens=5))
    )

    assert pedacos == ["ok"]
    assert len(pedidos) == 2
    assert "thinkingConfig" not in pedidos[1]["generationConfig"]


def test_uso_sem_padrao_usa_o_das_tarefas_e_depois_o_do_chat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "gemini_modelos", {})
    monkeypatch.setattr(settings, "gemini_modelo", "chat-x")
    monkeypatch.setattr(settings, "gemini_modelo_tarefas", "")
    assert settings.modelo_gemini("novo-uso") == "chat-x"
    monkeypatch.setattr(settings, "gemini_modelo_tarefas", "tarefas-y")
    assert settings.modelo_gemini("novo-uso") == "tarefas-y"
    assert settings.modelo_gemini("chat") == "chat-x"


def test_o_cliente_http_e_reaproveitado_no_mesmo_loop_e_novo_em_outro() -> None:
    from app.ia.gemini import _compartilhado

    async def dois_pedidos() -> tuple[httpx2.AsyncClient, httpx2.AsyncClient]:
        return _compartilhado("https://g.teste", "chave"), _compartilhado(
            "https://g.teste", "chave"
        )

    primeiro, segundo = asyncio.run(dois_pedidos())
    # Mesma conexão HTTPS nos dois pedidos do mesmo loop: sem novo aperto de mão TLS.
    assert primeiro is segundo
    # Outro `asyncio.run`, outro loop: o cliente do loop encerrado não serve mais.
    outro, _ = asyncio.run(dois_pedidos())
    assert outro is not primeiro


def test_o_padrao_de_raciocinio_e_o_mais_rapido() -> None:
    assert Settings().gemini_raciocinio == "minimal"


def erro_no_stream(code: int = 503, status: str = "UNAVAILABLE") -> bytes:
    """O Google às vezes responde 200 e manda a sobrecarga como evento de erro."""
    erro = {"error": {"code": code, "message": "high demand", "status": status}}
    return ("data: " + json.dumps(erro) + "\n\n").encode()


def test_erro_de_sobrecarga_dentro_do_stream_tenta_de_novo() -> None:
    respostas = iter(
        [
            httpx2.Response(200, content=erro_no_stream()),
            httpx2.Response(200, content=eventos("ok")),
        ]
    )

    pedacos = asyncio.run(coletar(gemini(lambda _: next(respostas)).gerar(MENSAGENS, max_tokens=5)))

    assert pedacos == ["ok"]


def test_modelo_sobrecarregado_passa_para_o_reserva() -> None:
    modelos: list[str] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        modelo = pedido.url.path.rsplit("/", 1)[-1].split(":")[0]
        modelos.append(modelo)
        if modelo == "gemini-2.5-flash":
            return httpx2.Response(200, content=erro_no_stream())
        return httpx2.Response(200, content=eventos("do reserva"))

    provedor = gemini(handler, tentativas=2)
    provedor.modelo_reserva = "gemini-3.1-flash-lite"
    pedacos = asyncio.run(coletar(provedor.gerar(MENSAGENS, max_tokens=5)))

    assert pedacos == ["do reserva"]
    assert modelos == ["gemini-2.5-flash", "gemini-2.5-flash", "gemini-3.1-flash-lite"]


def test_sobrecarga_depois_do_texto_nao_repete_a_resposta() -> None:
    chamadas = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal chamadas
        chamadas += 1
        return httpx2.Response(200, content=eventos("Um ") + erro_no_stream())

    provedor = gemini(handler, tentativas=3)
    provedor.modelo_reserva = "gemini-3.1-flash-lite"
    recebidos: list[str] = []

    async def consumir() -> None:
        async for pedaco in provedor.gerar(MENSAGENS, max_tokens=5):
            recebidos.append(pedaco)

    with pytest.raises(IAIndisponivel):
        asyncio.run(consumir())
    # O "Um " já foi entregue: nem nova tentativa nem reserva, que o duplicariam.
    assert recebidos == ["Um "]
    assert chamadas == 1


def test_erro_que_nao_e_sobrecarga_nao_vai_para_o_reserva() -> None:
    modelos: list[str] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        modelos.append(pedido.url.path)
        return httpx2.Response(200, content=erro_no_stream(code=400, status="INVALID_ARGUMENT"))

    provedor = gemini(handler)
    provedor.modelo_reserva = "gemini-3.1-flash-lite"
    with pytest.raises(IAIndisponivel):
        asyncio.run(coletar(provedor.gerar(MENSAGENS, max_tokens=5)))
    assert len(modelos) == 1


def test_extracao_em_json_cortada_no_meio_recomeca_e_entrega_inteira() -> None:
    respostas = iter(
        [
            httpx2.Response(200, content=eventos('{"assu') + erro_no_stream()),
            httpx2.Response(200, content=eventos('{"assuntos": ', '["laços"]}')),
        ]
    )
    formato = {"type": "object"}

    pedacos = asyncio.run(
        coletar(gemini(lambda _: next(respostas)).gerar(MENSAGENS, max_tokens=50, formato=formato))
    )

    # Sem o começo da tentativa cortada: um pedaço só, com o JSON inteiro.
    assert pedacos == ['{"assuntos": ["laços"]}']


def test_ementa_com_gemini_le_partes_maiores_e_em_paralelo(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ia.skills import ler_ementa
    from app.services import assuntos_ementa

    monkeypatch.setattr(settings, "ementa_tamanho_da_parte", 0)
    monkeypatch.setattr(settings, "ementa_leituras_simultaneas", 0)
    monkeypatch.setattr(settings, "ia_provedor", "ollama")
    assert assuntos_ementa.tamanho_da_parte() == ler_ementa.TAMANHO_DA_PARTE
    assert assuntos_ementa.leituras_simultaneas() == 1

    monkeypatch.setattr(settings, "ia_provedor", "gemini")
    assert assuntos_ementa.tamanho_da_parte() == 12_000
    assert assuntos_ementa.leituras_simultaneas() == 3

    monkeypatch.setattr(settings, "ementa_tamanho_da_parte", 8000)
    assert assuntos_ementa.tamanho_da_parte() == 8000


def test_leitura_em_paralelo_respeita_o_limite_e_mantem_a_ordem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import assuntos_ementa

    monkeypatch.setattr(settings, "ementa_leituras_simultaneas", 2)
    ao_mesmo_tempo = maximo = 0

    class Provedor:
        async def gerar(self, mensagens, *, max_tokens, formato=None):
            nonlocal ao_mesmo_tempo, maximo
            ao_mesmo_tempo += 1
            maximo = max(maximo, ao_mesmo_tempo)
            parte = mensagens[-1].conteudo
            numero = int(parte.split("PARTE-")[1].split()[0])
            # A primeira parte demora mais: termina depois das outras.
            await asyncio.sleep(0.05 if numero == 1 else 0.01)
            ao_mesmo_tempo -= 1
            yield json.dumps(
                {
                    "disciplinas": [
                        {"nome": f"Disciplina {numero}", "programacao": True, "assuntos": ["x"]}
                    ]
                }
            )

    partes = [f"PARTE-{i} texto" for i in range(1, 6)]
    leituras = asyncio.run(assuntos_ementa._ler(Provedor(), partes))

    assert maximo == 2
    assert [leitura.disciplinas[0].nome for leitura in leituras] == [
        f"Disciplina {i}" for i in range(1, 6)
    ]


def cota_por_minuto(segundos: str) -> httpx2.Response:
    return httpx2.Response(
        429,
        json={
            "error": {
                "code": 429,
                "message": "Quota exceeded for metric: embed_content_free_tier_requests",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": segundos}
                ],
            }
        },
    )


def test_embeddings_esperam_a_cota_por_minuto_virar(monkeypatch: pytest.MonkeyPatch) -> None:
    esperas: list[float] = []

    async def dormir(segundos: float) -> None:
        esperas.append(segundos)

    monkeypatch.setattr("app.ia.gemini.asyncio.sleep", dormir)
    respostas = iter(
        [
            cota_por_minuto("52s"),
            httpx2.Response(200, json={"embeddings": [{"values": [1.0] * DIMENSOES_EMBEDDING}]}),
        ]
    )

    vetores = asyncio.run(gemini(lambda _: next(respostas), tentativas=1).embeddings(["a"]))

    assert len(vetores) == 1
    # Esperou o que o Google pediu (+1 s de folga), sem gastar a única tentativa.
    assert esperas == [53.0]


def test_embeddings_sem_cota_do_dia_desistem_na_hora(monkeypatch: pytest.MonkeyPatch) -> None:
    esperas: list[float] = []

    async def dormir(segundos: float) -> None:
        esperas.append(segundos)

    monkeypatch.setattr("app.ia.gemini.asyncio.sleep", dormir)

    with pytest.raises(IAIndisponivel, match="429"):
        asyncio.run(gemini(lambda _: cota_por_minuto("43200s"), tentativas=1).embeddings(["a"]))
    assert esperas == []
