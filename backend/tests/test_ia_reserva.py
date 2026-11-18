"""Gemini com o Ollama de reserva, um modelo por uso e embeddings no Ollama."""

import asyncio
from collections.abc import AsyncGenerator

import pytest

from app.core.config import settings
from app.ia import IAIndisponivel, MensagemIA, get_provedor_ia, get_provedor_ia_tarefas, para
from app.ia.gemini import Gemini
from app.ia.ollama import Ollama
from app.ia.reserva import ComReserva, PorUso, limpar_pausas

MENSAGENS = [MensagemIA("user", "Oi")]


class Falso:
    """Responde `pedacos`; com `falhar_depois`, levanta depois de mandar tantos pedaços."""

    def __init__(self, *pedacos: str, falhar_depois: int | None = None) -> None:
        self.pedacos = pedacos
        self.falhar_depois = falhar_depois
        self.chamadas = 0

    async def gerar(self, mensagens, *, max_tokens, formato=None) -> AsyncGenerator[str]:
        self.chamadas += 1
        for i, pedaco in enumerate(self.pedacos):
            if self.falhar_depois is not None and i == self.falhar_depois:
                raise IAIndisponivel("cota esgotada")
            yield pedaco
        if self.falhar_depois is not None and self.falhar_depois >= len(self.pedacos):
            raise IAIndisponivel("cota esgotada")

    async def embeddings(self, textos):
        return [[1.0] for _ in textos]


def coletar(provedor) -> list[str]:
    async def tudo() -> list[str]:
        return [p async for p in provedor.gerar(MENSAGENS, max_tokens=10)]

    return asyncio.run(tudo())


@pytest.fixture(autouse=True)
def sem_pausas() -> None:
    limpar_pausas()


def test_principal_respondendo_a_reserva_nem_e_chamada() -> None:
    principal, reserva = Falso("do ", "gemini"), Falso("ollama")

    assert coletar(ComReserva(principal, reserva, nome="m", pausa_segundos=60)) == [
        "do ",
        "gemini",
    ]
    assert reserva.chamadas == 0


def test_principal_falhando_antes_de_responder_vai_para_a_reserva() -> None:
    principal, reserva = Falso("x", falhar_depois=0), Falso("do ollama")

    assert coletar(ComReserva(principal, reserva, nome="m", pausa_segundos=60)) == ["do ollama"]


def test_falha_no_meio_da_resposta_nao_emenda_outro_modelo() -> None:
    principal, reserva = Falso("meia ", "resposta", falhar_depois=1), Falso("outra")

    with pytest.raises(IAIndisponivel):
        coletar(ComReserva(principal, reserva, nome="m", pausa_segundos=60))
    assert reserva.chamadas == 0


def test_depois_da_falha_o_modelo_fica_pausado_e_vai_direto_para_a_reserva() -> None:
    agora = [100.0]
    principal, reserva = Falso("x", falhar_depois=0), Falso("ok")

    def provedor() -> ComReserva:
        return ComReserva(principal, reserva, nome="m", pausa_segundos=60, relogio=lambda: agora[0])

    coletar(provedor())
    coletar(provedor())
    # Na segunda vez o principal nem foi chamado: estava pausado.
    assert principal.chamadas == 1

    agora[0] += 61
    coletar(provedor())
    assert principal.chamadas == 2


def test_pausado_com_a_reserva_fora_do_ar_ainda_tenta_o_principal() -> None:
    """Com o Ollama desligado, um 503 passageiro do Gemini não derruba o minuto seguinte."""
    principal, reserva = Falso("x", falhar_depois=0), Falso("y", falhar_depois=0)
    with pytest.raises(IAIndisponivel):
        coletar(ComReserva(principal, reserva, nome="m", pausa_segundos=60))

    principal.falhar_depois = None  # o Gemini voltou
    assert coletar(ComReserva(principal, reserva, nome="m", pausa_segundos=60)) == ["x"]
    # E, tendo respondido, sai da pausa: o próximo nem passa pela reserva.
    chamadas = reserva.chamadas
    coletar(ComReserva(principal, reserva, nome="m", pausa_segundos=60))
    assert reserva.chamadas == chamadas


def test_reserva_tambem_fora_do_ar_sobe_o_erro() -> None:
    principal, reserva = Falso("x", falhar_depois=0), Falso("y", falhar_depois=0)

    with pytest.raises(IAIndisponivel):
        coletar(ComReserva(principal, reserva, nome="m", pausa_segundos=60))


def test_por_uso_monta_um_provedor_por_uso_e_embeddings_de_um_so() -> None:
    criados: list[str] = []
    embeddings = Falso()

    def fabrica(uso: str) -> Falso:
        criados.append(uso)
        return Falso(uso)

    roteador = PorUso(fabrica, embeddings, uso_padrao="chat")

    assert coletar(roteador) == ["chat"]
    assert coletar(para(roteador, "correcao")) == ["correcao"]
    para(roteador, "correcao")
    assert criados == ["chat", "correcao"]
    assert asyncio.run(roteador.embeddings(["a", "b"])) == [[1.0], [1.0]]


def test_para_devolve_o_proprio_provedor_sem_usos() -> None:
    falso = Falso("x")
    assert para(falso, "correcao") is falso


def test_gemini_com_reserva_e_embeddings_no_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ia_provedor", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "chave")
    monkeypatch.setattr(settings, "ia_reserva", "ollama")
    monkeypatch.setattr(settings, "ia_provedor_embeddings", "ollama")
    monkeypatch.setattr(settings, "ollama_modelo", "llama3.2")
    monkeypatch.setattr(settings, "ollama_modelo_tarefas", "llama3.2:1b")

    chat, tarefas = get_provedor_ia(), get_provedor_ia_tarefas()

    do_chat = para(chat, "chat")
    assert isinstance(do_chat, ComReserva)
    assert isinstance(do_chat.principal, Gemini) and isinstance(do_chat.reserva, Ollama)
    assert do_chat.reserva.modelo == "llama3.2"
    # O segundo plano cai no modelo de tarefas do Ollama.
    assert para(tarefas, "ementa").reserva.modelo == "llama3.2:1b"
    assert isinstance(chat.provedor_de_embeddings, Ollama)
    # O Ollama não marca o embedding (ver `vault/ingestao.py`).
    assert chat.marca_embedding is None


def test_sem_reserva_o_uso_e_o_gemini_puro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ia_provedor", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "chave")
    monkeypatch.setattr(settings, "ia_reserva", "")
    monkeypatch.setattr(settings, "ia_provedor_embeddings", "")

    chat = get_provedor_ia()

    assert isinstance(para(chat, "correcao"), Gemini)
    assert isinstance(chat.provedor_de_embeddings, Gemini)


def test_configuracao_recusa_provedor_desconhecido() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="IA_RESERVA"):
        Settings(ia_reserva="openai")
    with pytest.raises(ValidationError, match="GEMINI_MODELOS"):
        Settings(gemini_modelos={"inventado": "x"})


def test_ollama_pede_para_manter_o_modelo_carregado_e_aquece() -> None:
    import json

    import httpx2

    pedidos: list[tuple[str, dict]] = []

    def handler(pedido: httpx2.Request) -> httpx2.Response:
        pedidos.append((pedido.url.path, json.loads(pedido.content)))
        if pedido.url.path == "/api/generate":
            return httpx2.Response(200, json={"done": True})
        linha = json.dumps({"message": {"content": "oi"}, "done": True})
        return httpx2.Response(200, content=linha.encode())

    ollama = Ollama(
        "http://ollama",
        "llama3.2",
        timeout_conexao=1,
        timeout_leitura=1,
        tentativas=1,
        manter_carregado="30m",
        transport=httpx2.MockTransport(handler),
    )

    asyncio.run(ollama.aquecer())
    assert coletar(ollama) == ["oi"]

    assert pedidos[0] == ("/api/generate", {"model": "llama3.2", "keep_alive": "30m"})
    assert pedidos[1][0] == "/api/chat" and pedidos[1][1]["keep_alive"] == "30m"


def test_aquecer_a_reserva_sem_ollama_nao_derruba_a_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ia.provedor import aquecer_reserva

    monkeypatch.setattr(settings, "ia_reserva", "ollama")
    monkeypatch.setattr(settings, "ollama_manter_carregado", "30m")
    monkeypatch.setattr(settings, "ollama_url", "http://127.0.0.1:9")

    asyncio.run(aquecer_reserva())  # só avisa no log
