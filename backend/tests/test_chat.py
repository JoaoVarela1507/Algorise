"""Chat com IA (#11): cliente do Ollama, skill do tutor e a rota em streaming.

O Ollama de verdade não entra aqui: o cliente é testado com o `MockTransport`
do httpx2, que responde exatamente o que o Ollama responde (uma linha JSON por
pedaço), e a rota com um provedor falso injetado pela dependência.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Iterator, Sequence
from datetime import UTC, datetime, timedelta

import fakeredis
import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.chat import transmitir
from app.core.config import Settings, settings
from app.ia import IAIndisponivel, MensagemIA, get_provedor_ia
from app.ia.eco import Eco
from app.ia.ollama import Ollama
from app.ia.skills import tutor
from app.main import app
from app.models import (
    Conversa,
    Curso,
    Instituicao,
    MensagemChat,
    ModoResposta,
    Modulo,
    NivelExperiencia,
    PapelMensagem,
    ProgressoUsuario,
    StatusProgresso,
    Trilha,
    Usuario,
)
from app.services import auth as servico_auth
from app.services import chat, conta
from tests.conftest import SENHA_VALIDA

ROTA = "/api/v1/chat/mensagens"


# --- provedor falso e leitura do SSE -------------------------------------------


class ProvedorFalso:
    """Responde `pedacos`, guarda o que recebeu e falha onde o teste mandar."""

    def __init__(self) -> None:
        self.pedacos: list[str] = ["Recursão ", "é uma função ", "que chama a si mesma."]
        self.falhar_antes = False
        self.falhar_depois_de: int | None = None
        self.chamadas: list[tuple[list[MensagemIA], int]] = []

    async def gerar(
        self, mensagens: Sequence[MensagemIA], *, max_tokens: int
    ) -> AsyncGenerator[str]:
        self.chamadas.append((list(mensagens), max_tokens))
        if self.falhar_antes:
            raise IAIndisponivel("Ollama fora (simulado)")
        for i, pedaco in enumerate(self.pedacos):
            if self.falhar_depois_de is not None and i == self.falhar_depois_de:
                raise IAIndisponivel("Ollama caiu no meio (simulado)")
            yield pedaco

    @property
    def contexto(self) -> list[MensagemIA]:
        return self.chamadas[-1][0]


@pytest.fixture
def provedor() -> Iterator[ProvedorFalso]:
    falso = ProvedorFalso()
    app.dependency_overrides[get_provedor_ia] = lambda: falso
    try:
        yield falso
    finally:
        app.dependency_overrides.pop(get_provedor_ia, None)


def eventos(corpo: str) -> list[tuple[str, dict]]:
    """`event:`/`data:` de cada bloco do SSE, na ordem."""
    lidos = []
    for bloco in corpo.strip().split("\n\n"):
        campos = dict(linha.split(": ", 1) for linha in bloco.splitlines())
        lidos.append((campos["event"], json.loads(campos["data"])))
    return lidos


def enviar(cliente: TestClient, headers: dict[str, str], conteudo: str, **extra) -> list:
    resposta = cliente.post(ROTA, headers=headers, json={"conteudo": conteudo, **extra})
    assert resposta.status_code == 200, resposta.text
    assert resposta.headers["content-type"].startswith("text/event-stream")
    return eventos(resposta.text)


# --- rota ----------------------------------------------------------------------


def test_primeira_mensagem_abre_conversa_e_responde_em_streaming(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso, db: Session
) -> None:
    lidos = enviar(cliente, autenticado, "Me explica recursão com um exemplo")

    nomes = [nome for nome, _ in lidos]
    assert nomes == ["chat.conversa", "chat.token", "chat.token", "chat.token", "chat.fim"]
    inicio = lidos[0][1]
    assert inicio["titulo"] == "Me explica recursão com um exemplo"
    texto = "".join(dados["texto"] for nome, dados in lidos if nome == "chat.token")
    assert texto == "Recursão é uma função que chama a si mesma."

    gravadas = db.scalars(select(MensagemChat).order_by(MensagemChat.id)).all()
    assert [(m.papel, m.conteudo, m.incompleta) for m in gravadas] == [
        (PapelMensagem.usuario, "Me explica recursão com um exemplo", False),
        (PapelMensagem.assistente, texto, False),
    ]
    assert gravadas[0].conversa_id == inicio["conversa_id"]
    assert inicio["mensagem_id"] == gravadas[0].id
    assert lidos[-1][1] == {"mensagem_id": gravadas[1].id}


def test_acento_vai_como_texto_no_sse(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso
) -> None:
    resposta = cliente.post(ROTA, headers=autenticado, json={"conteudo": "o que é recursão?"})

    assert "Recursão" in resposta.text
    assert "\\u00e3" not in resposta.text


def test_mensagem_seguinte_leva_o_historico_ao_modelo(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso
) -> None:
    conversa_id = enviar(cliente, autenticado, "O que é recursão?")[0][1]["conversa_id"]

    lidos = enviar(cliente, autenticado, "E o caso base?", conversa_id=conversa_id)

    assert lidos[0][1]["conversa_id"] == conversa_id
    papeis = [(m.papel, m.conteudo) for m in provedor.contexto]
    assert papeis[0][0] == "system"
    assert papeis[1:] == [
        ("user", "O que é recursão?"),
        ("assistant", "Recursão é uma função que chama a si mesma."),
        ("user", "E o caso base?"),
    ]


def test_historico_enviado_ao_modelo_tem_janela(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "chat_janela_historico", 2)
    conversa_id = enviar(cliente, autenticado, "primeira")[0][1]["conversa_id"]
    enviar(cliente, autenticado, "segunda", conversa_id=conversa_id)

    enviar(cliente, autenticado, "terceira", conversa_id=conversa_id)

    # Sistema, as duas mais recentes (pergunta e resposta da "segunda") e a nova.
    assert [m.conteudo for m in provedor.contexto[1:]] == [
        "segunda",
        "Recursão é uma função que chama a si mesma.",
        "terceira",
    ]


def test_conversa_de_outro_aluno_responde_404(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,
    db: Session,
) -> None:
    outro = servico_auth.registrar(
        db, email="bia@ufrpe.br", senha=SENHA_VALIDA, username="bia", nome_exibicao="Bia"
    )
    alheia = Conversa(usuario_id=outro.id, titulo="Particular")
    db.add(alheia)
    db.commit()

    for conversa_id in (alheia.id, 9999):
        resposta = cliente.post(
            ROTA, headers=autenticado, json={"conteudo": "oi", "conversa_id": conversa_id}
        )
        assert resposta.status_code == 404
        assert resposta.json()["erro"]["code"] == "conversa_nao_encontrada"

    assert provedor.chamadas == []
    assert db.scalar(select(func.count()).select_from(MensagemChat)) == 0


def test_ia_fora_antes_de_responder_da_503_sem_gravar(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso, db: Session
) -> None:
    provedor.falhar_antes = True

    resposta = cliente.post(ROTA, headers=autenticado, json={"conteudo": "oi"})

    assert resposta.status_code == 503
    erro = resposta.json()["erro"]
    assert erro["code"] == "ia_indisponivel"
    # O motivo técnico (endereço, modelo) fica no log, não na tela.
    assert "Ollama" not in erro["message"]
    assert db.scalar(select(func.count()).select_from(Conversa)) == 0
    assert db.scalar(select(func.count()).select_from(MensagemChat)) == 0


def test_ia_que_cai_no_meio_salva_o_parcial_como_incompleto(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso, db: Session
) -> None:
    provedor.falhar_depois_de = 2

    lidos = enviar(cliente, autenticado, "O que é recursão?")

    assert [nome for nome, _ in lidos] == [
        "chat.conversa",
        "chat.token",
        "chat.token",
        "chat.erro",
    ]
    resposta = db.scalars(
        select(MensagemChat).where(MensagemChat.papel == PapelMensagem.assistente)
    ).one()
    assert resposta.conteudo == "Recursão é uma função "
    assert resposta.incompleta is True
    assert lidos[-1][1]["code"] == "ia_indisponivel"
    assert lidos[-1][1]["mensagem_id"] == resposta.id


def test_aluno_que_fecha_a_aba_deixa_o_parcial_gravado(
    sessao_factory: sessionmaker[Session], db: Session, usuario: Usuario
) -> None:
    conversa = Conversa(usuario_id=usuario.id, titulo="Recursão")
    db.add(conversa)
    db.commit()

    async def sem_fim() -> AsyncGenerator[str]:
        yield "é uma função "
        while True:
            yield "..."
            await asyncio.sleep(0)

    async def cenario() -> None:
        stream = transmitir(sem_fim(), "Recursão ", sessao_factory, {"conversa_id": conversa.id})
        # Evento da conversa, o primeiro pedaço e o segundo; aí o aluno sai.
        for _ in range(3):
            await anext(stream)
        await stream.aclose()

    asyncio.run(cenario())

    db.expire_all()
    resposta = db.scalars(select(MensagemChat)).one()
    assert resposta.conteudo == "Recursão é uma função "
    assert resposta.incompleta is True


def test_resposta_vazia_nao_grava_mensagem_do_assistente(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso, db: Session
) -> None:
    provedor.pedacos = []

    lidos = enviar(cliente, autenticado, "oi")

    assert lidos[-1] == ("chat.fim", {"mensagem_id": None})
    assert db.scalars(select(MensagemChat.papel)).all() == [PapelMensagem.usuario]


def test_chat_exige_login(cliente: TestClient, provedor: ProvedorFalso) -> None:
    assert cliente.post(ROTA, json={"conteudo": "oi"}).status_code == 401


@pytest.mark.parametrize("conteudo", ["", "   \n ", "x" * (settings.chat_maximo_caracteres + 1)])
def test_mensagem_vazia_ou_longa_demais_e_recusada(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso, conteudo: str
) -> None:
    resposta = cliente.post(ROTA, headers=autenticado, json={"conteudo": conteudo})

    assert resposta.status_code == 422
    assert provedor.chamadas == []


def test_modo_muda_instrucao_e_limite_de_tokens(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso
) -> None:
    enviar(cliente, autenticado, "oi", modo="rapido")
    rapido_sistema, rapido_tokens = provedor.chamadas[-1][0][0].conteudo, provedor.chamadas[-1][1]
    enviar(cliente, autenticado, "oi", modo="detalhado")
    detalhado_sistema, detalhado_tokens = (
        provedor.chamadas[-1][0][0].conteudo,
        provedor.chamadas[-1][1],
    )

    assert "três frases" in rapido_sistema
    assert "exercício" in detalhado_sistema
    assert rapido_tokens < detalhado_tokens


def test_modo_desconhecido_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorFalso
) -> None:
    resposta = cliente.post(ROTA, headers=autenticado, json={"conteudo": "oi", "modo": "turbo"})

    assert resposta.status_code == 422


def test_rate_limit_do_chat_por_aluno(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rate_limit_chat_requisicoes", 2)

    for _ in range(2):
        enviar(cliente, autenticado, "oi")
    barrada = cliente.post(ROTA, headers=autenticado, json={"conteudo": "oi"})

    assert barrada.status_code == 429
    assert "Retry-After" in barrada.headers
    assert len(provedor.chamadas) == 2


def test_chat_continua_com_o_redis_fora(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,
    redis_fora: None,
) -> None:
    # Sem o Redis o rate limit libera (falha aberto): o chat não cai junto.
    assert enviar(cliente, autenticado, "oi")[-1][0] == "chat.fim"


def test_prompt_leva_o_contexto_do_aluno(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,
    db: Session,
    usuario: Usuario,
) -> None:
    instituicao = Instituicao(nome="Universidade Federal Rural de Pernambuco", sigla="UFRPE")
    curso = Curso(instituicao=instituicao, nome="Bacharelado em Sistemas de Informação")
    trilha = Trilha(slug="python", nome="Introdução a Python", disciplina="Algoritmos", periodo=1)
    modulo = Modulo(trilha=trilha, ordem=1, titulo="Laços de repetição")
    db.add_all([instituicao, curso, trilha, modulo])
    db.flush()
    db.add(
        ProgressoUsuario(
            usuario_id=usuario.id,
            trilha_id=trilha.id,
            modulo_id=modulo.id,
            status=StatusProgresso.em_andamento,
        )
    )
    aluno = db.get_one(Usuario, usuario.id)
    aluno.instituicao_id, aluno.curso_id, aluno.periodo = instituicao.id, curso.id, 3
    db.commit()

    enviar(cliente, autenticado, "oi")

    sistema = provedor.contexto[0].conteudo
    assert (
        "Cursa Bacharelado em Sistemas de Informação na Universidade Federal Rural de "
        "Pernambuco, no 3º período." in sistema
    )
    assert 'trilha "Introdução a Python" (Algoritmos), no módulo "Laços de repetição"' in sistema


def test_expurgo_da_conta_apaga_as_conversas(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,
    db: Session,
    usuario: Usuario,
    redis_falso: fakeredis.FakeRedis,
) -> None:
    enviar(cliente, autenticado, "oi")
    aluno = db.get_one(Usuario, usuario.id)
    conta.agendar_exclusao(db, aluno, confirmacao="EXCLUIR", senha=SENHA_VALIDA)

    vencido = datetime.now(UTC) + timedelta(days=settings.prazo_exclusao_dias + 1)
    assert conta.expurgar_vencidas(db, agora=vencido) == 1

    assert db.scalar(select(func.count()).select_from(Conversa)) == 0
    assert db.scalar(select(func.count()).select_from(MensagemChat)) == 0


# --- serviço e skill -----------------------------------------------------------


def test_titulo_sai_da_primeira_linha() -> None:
    assert chat.titulo_de("  Como   faço\num laço?") == "Como faço"
    longo = chat.titulo_de("palavra " * 30)
    assert len(longo) == chat.TAMANHO_DO_TITULO
    assert longo.endswith("…")


def test_tutor_sem_curso_nao_cita_curso() -> None:
    texto = tutor.instrucao(tutor.Aluno(nivel=NivelExperiencia.baixo), ModoResposta.medio)

    assert "Cursa" not in texto
    assert "Estuda" not in texto
    assert 'trilha "' not in texto
    assert "começando a programar" in texto


def test_tutor_so_com_instituicao() -> None:
    aluno = tutor.Aluno(nivel=NivelExperiencia.alto, instituicao="UFPE", periodo=2)

    assert "- Estuda na UFPE, no 2º período." in tutor.instrucao(aluno, ModoResposta.medio)


def test_tutor_monta_mensagens_na_ordem() -> None:
    historico = [MensagemIA("user", "a"), MensagemIA("assistant", "b")]

    mensagens = tutor.mensagens(
        tutor.Aluno(nivel=NivelExperiencia.medio), ModoResposta.rapido, historico, "c"
    )

    assert [m.papel for m in mensagens] == ["system", "user", "assistant", "user"]
    assert mensagens[-1].conteudo == "c"


# --- provedores ----------------------------------------------------------------


async def coletar(fluxo: AsyncGenerator[str]) -> list[str]:
    return [pedaco async for pedaco in fluxo]


def linhas_do_ollama(*pedacos: str, done: bool = True) -> bytes:
    linhas = [
        json.dumps({"message": {"role": "assistant", "content": p}, "done": False}) for p in pedacos
    ]
    if done:
        linhas.append(json.dumps({"message": {"content": ""}, "done": True}))
    return ("\n".join(linhas) + "\n").encode()


def ollama(handler, *, tentativas: int = 2) -> Ollama:
    return Ollama(
        "http://ollama.teste",
        "llama3.2",
        timeout_conexao=1,
        timeout_leitura=1,
        tentativas=tentativas,
        espera_entre_tentativas=0,
        transport=httpx2.MockTransport(handler),
    )


MENSAGENS = [MensagemIA("system", "Seja breve."), MensagemIA("user", "O que é um laço?")]


def test_ollama_transmite_os_pedacos_e_manda_o_pedido_certo() -> None:
    pedidos: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        pedidos.append(request)
        return httpx2.Response(200, content=linhas_do_ollama("Um laço ", "repete."))

    pedacos = asyncio.run(coletar(ollama(handler).gerar(MENSAGENS, max_tokens=42)))

    assert pedacos == ["Um laço ", "repete."]
    assert pedidos[0].url.path == "/api/chat"
    corpo = json.loads(pedidos[0].content)
    assert corpo == {
        "model": "llama3.2",
        "stream": True,
        "messages": [
            {"role": "system", "content": "Seja breve."},
            {"role": "user", "content": "O que é um laço?"},
        ],
        "options": {"num_predict": 42},
    }


def test_ollama_tenta_de_novo_quando_nao_conecta() -> None:
    tentativas = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        tentativas.append(request)
        if len(tentativas) == 1:
            raise httpx2.ConnectError("recusada", request=request)
        return httpx2.Response(200, content=linhas_do_ollama("ok"))

    assert asyncio.run(coletar(ollama(handler).gerar(MENSAGENS, max_tokens=5))) == ["ok"]
    assert len(tentativas) == 2


def test_ollama_fora_vira_ia_indisponivel_depois_das_tentativas() -> None:
    tentativas = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        tentativas.append(request)
        raise httpx2.ConnectError("recusada", request=request)

    with pytest.raises(IAIndisponivel, match="Sem conexão"):
        asyncio.run(coletar(ollama(handler, tentativas=3).gerar(MENSAGENS, max_tokens=5)))
    assert len(tentativas) == 3


def test_modelo_ausente_nao_tenta_de_novo() -> None:
    tentativas = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        tentativas.append(request)
        return httpx2.Response(404, json={"error": "model 'llama3.2' not found"})

    with pytest.raises(IAIndisponivel, match="not found"):
        asyncio.run(coletar(ollama(handler).gerar(MENSAGENS, max_tokens=5)))
    assert len(tentativas) == 1


def test_erro_no_meio_do_stream_vira_ia_indisponivel_depois_do_parcial() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        corpo = linhas_do_ollama("Um ", done=False) + b'{"error":"out of memory"}\n'
        return httpx2.Response(200, content=corpo)

    recebidos: list[str] = []

    async def consumir() -> None:
        async for pedaco in ollama(handler).gerar(MENSAGENS, max_tokens=5):
            recebidos.append(pedaco)

    with pytest.raises(IAIndisponivel, match="out of memory"):
        asyncio.run(consumir())
    assert recebidos == ["Um "]


def test_stream_cortado_sem_done_vira_ia_indisponivel() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=linhas_do_ollama("Um ", done=False))

    with pytest.raises(IAIndisponivel, match="sem concluir"):
        asyncio.run(coletar(ollama(handler).gerar(MENSAGENS, max_tokens=5)))


def test_timeout_de_leitura_nao_tenta_de_novo() -> None:
    tentativas = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        tentativas.append(request)
        raise httpx2.ReadTimeout("lento", request=request)

    with pytest.raises(IAIndisponivel, match="demorou"):
        asyncio.run(coletar(ollama(handler).gerar(MENSAGENS, max_tokens=5)))
    assert len(tentativas) == 1


def test_resposta_fora_do_formato_vira_ia_indisponivel() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"<html>proxy</html>\n")

    with pytest.raises(IAIndisponivel, match="formato"):
        asyncio.run(coletar(ollama(handler).gerar(MENSAGENS, max_tokens=5)))


def test_eco_devolve_a_pergunta_em_pedacos() -> None:
    pedacos = asyncio.run(coletar(Eco().gerar(MENSAGENS, max_tokens=100)))

    assert len(pedacos) > 1
    assert "".join(pedacos) == "Você perguntou: O que é um laço?"


def test_provedor_padrao_e_o_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(get_provedor_ia(), Ollama)
    monkeypatch.setattr(settings, "ia_provedor", "eco")
    assert isinstance(get_provedor_ia(), Eco)


def test_producao_nao_sobe_com_o_provedor_de_teste() -> None:
    segredo = "s" * 40
    with pytest.raises(ValidationError, match="IA_PROVEDOR"):
        Settings(environment="production", jwt_secret=segredo, ia_provedor="eco")
    with pytest.raises(ValidationError, match="IA_PROVEDOR"):
        Settings(ia_provedor="openai")
    assert Settings(environment="production", jwt_secret=segredo).ia_provedor == "ollama"
