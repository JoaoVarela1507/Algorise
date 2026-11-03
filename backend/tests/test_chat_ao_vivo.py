"""Chat pelo WebSocket (#36): a resposta em pedaços no canal da conversa,
parar, as abas sincronizadas e o parcial gravado em todo final."""

import asyncio
import time
from collections.abc import AsyncGenerator, Iterator, Sequence
from typing import Any

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import WebSocketTestSession

from app.core.seguranca import criar_access_token
from app.ia import IAIndisponivel, MensagemIA, get_provedor_ia
from app.main import app
from app.models import Conversa, MensagemChat, PapelMensagem, Usuario
from app.services import chat_ao_vivo, tempo_real

URL = "/api/v1/ws"


class ProvedorFalso:
    """Responde `pedacos`, um a um, com `pausa` entre eles."""

    def __init__(self) -> None:
        self.pedacos: list[str] = ["Olá", ", ", "aluno"]
        self.pausa = 0.0
        self.sem_fim = False
        self.falhar_antes = False
        self.falhar_depois_de: int | None = None
        self.fechado = False

    async def gerar(
        self, mensagens: Sequence[MensagemIA], *, max_tokens: int, formato: Any = None
    ) -> AsyncGenerator[str]:
        if self.falhar_antes:
            raise IAIndisponivel("fora")
        try:
            i = 0
            while True:
                if self.sem_fim:
                    pedaco = f"p{i} "
                elif i < len(self.pedacos):
                    pedaco = self.pedacos[i]
                else:
                    return
                if self.falhar_depois_de is not None and i >= self.falhar_depois_de:
                    raise IAIndisponivel("caiu")
                if self.pausa:
                    await asyncio.sleep(self.pausa)
                yield pedaco
                i += 1
        finally:
            self.fechado = True


@pytest.fixture
def provedor() -> Iterator[ProvedorFalso]:
    falso = ProvedorFalso()
    app.dependency_overrides[get_provedor_ia] = lambda: falso
    yield falso
    app.dependency_overrides.pop(get_provedor_ia, None)


@pytest.fixture(autouse=True)
def ouvinte_limpo(redis_falso: fakeredis.FakeRedis) -> Iterator[None]:
    tempo_real.ouvinte.parar()
    yield
    tempo_real.ouvinte.parar()


@pytest.fixture
def token(usuario: Usuario) -> str:
    return criar_access_token(usuario.id)


def entrar(ws: WebSocketTestSession, token: str) -> None:
    ws.send_json({"tipo": "autenticar", "token": token})
    assert ws.receive_json()["tipo"] == "autenticado"
    assert tempo_real.ouvinte.inscrito.wait(timeout=5)


def perguntar(ws: WebSocketTestSession, conteudo: str = "O que é um laço?", **extra: Any) -> None:
    ws.send_json({"tipo": "chat.mensagem.enviar", "conteudo": conteudo, **extra})


def ate(ws: WebSocketTestSession, *eventos: str) -> list[dict[str, Any]]:
    """Recebe até chegar um dos eventos finais; devolve tudo o que veio."""
    recebidas = []
    while True:
        mensagem = ws.receive_json()
        recebidas.append(mensagem)
        if mensagem.get("evento") in eventos or mensagem.get("tipo") == "erro":
            return recebidas


def nomes(recebidas: list[dict[str, Any]]) -> list[str]:
    return [m.get("evento") or m["tipo"] for m in recebidas]


def texto(recebidas: list[dict[str, Any]]) -> str:
    return "".join(m["payload"]["texto"] for m in recebidas if m.get("evento") == "chat.token")


def respostas(fabrica: sessionmaker[Session]) -> list[MensagemChat]:
    with fabrica() as db:
        return list(
            db.scalars(select(MensagemChat).where(MensagemChat.papel == PapelMensagem.assistente))
        )


# --- fluxo principal ----------------------------------------------------------------------


def test_conversa_nova_responde_em_pedacos_e_grava(
    cliente: TestClient, token: str, provedor: ProvedorFalso, sessao_factory: sessionmaker[Session]
) -> None:
    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        perguntar(ws)
        recebidas = ate(ws, "chat.fim")

    assert nomes(recebidas) == [
        "inscrito",
        "chat.conversa",
        "chat.token",
        "chat.token",
        "chat.token",
        "chat.fim",
    ]
    inicio = recebidas[1]["payload"]
    assert inicio["pergunta"] == "O que é um laço?"
    assert recebidas[0]["canal"] == f"chat:{inicio['conversa_id']}"
    assert texto(recebidas) == "Olá, aluno"
    [resposta] = respostas(sessao_factory)
    assert (resposta.conteudo, resposta.incompleta) == ("Olá, aluno", False)
    assert recebidas[-1]["payload"]["mensagem_id"] == resposta.id


def test_outra_aba_acompanha_a_mesma_geracao(
    cliente: TestClient, token: str, provedor: ProvedorFalso, db: Session, usuario: Usuario
) -> None:
    conversa = Conversa(usuario_id=usuario.id, titulo="Laços")
    db.add(conversa)
    db.commit()
    canal = f"chat:{conversa.id}"

    with cliente.websocket_connect(URL) as aba1, cliente.websocket_connect(URL) as aba2:
        for aba in (aba1, aba2):
            entrar(aba, token)
            aba.send_json({"tipo": "inscrever", "canal": canal})
            aba.receive_json()
        perguntar(aba1, conversa_id=conversa.id)

        da_aba1 = ate(aba1, "chat.fim")
        da_aba2 = ate(aba2, "chat.fim")

    assert nomes(da_aba1) == nomes(da_aba2)
    assert texto(da_aba2) == "Olá, aluno"


def test_digitando_chega_nas_outras_abas(
    cliente: TestClient, token: str, provedor: ProvedorFalso, db: Session, usuario: Usuario
) -> None:
    conversa = Conversa(usuario_id=usuario.id, titulo="Laços")
    db.add(conversa)
    db.commit()

    with cliente.websocket_connect(URL) as aba1, cliente.websocket_connect(URL) as aba2:
        entrar(aba1, token)
        entrar(aba2, token)
        aba2.send_json({"tipo": "inscrever", "canal": f"chat:{conversa.id}"})
        aba2.receive_json()

        aba1.send_json({"tipo": "chat.digitando", "conversa_id": conversa.id})

        assert aba2.receive_json()["evento"] == "chat.digitando"


# --- parar --------------------------------------------------------------------------------


def test_parar_interrompe_e_grava_o_parcial(
    cliente: TestClient, token: str, provedor: ProvedorFalso, sessao_factory: sessionmaker[Session]
) -> None:
    provedor.sem_fim = True
    provedor.pausa = 0.02

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        perguntar(ws)
        ws.receive_json()  # inscrito
        conversa_id = ws.receive_json()["payload"]["conversa_id"]
        assert ws.receive_json()["evento"] == "chat.token"

        ws.send_json({"tipo": "chat.parar", "conversa_id": conversa_id})
        recebidas = ate(ws, "chat.parado")

    assert recebidas[-1]["evento"] == "chat.parado"
    assert provedor.fechado
    [resposta] = respostas(sessao_factory)
    assert resposta.incompleta is True
    assert resposta.conteudo.startswith("p0 ")


def test_parar_pedido_por_outra_instancia_vale(
    cliente: TestClient,
    token: str,
    provedor: ProvedorFalso,
    redis_falso: fakeredis.FakeRedis,
    sessao_factory: sessionmaker[Session],
) -> None:
    provedor.sem_fim = True
    provedor.pausa = 0.02

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        perguntar(ws)
        ws.receive_json()
        conversa_id = ws.receive_json()["payload"]["conversa_id"]
        ws.receive_json()

        # O que a outra instância faz: só a marca no Redis.
        redis_falso.set(f"chat:parar:{conversa_id}", "1")
        recebidas = ate(ws, "chat.parado")

    assert recebidas[-1]["evento"] == "chat.parado"
    assert respostas(sessao_factory)[0].incompleta is True


def test_parar_conversa_de_outro_aluno_e_negado(
    cliente: TestClient, token: str, provedor: ProvedorFalso, db: Session
) -> None:
    dona = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(dona)
    db.commit()
    alheia = Conversa(usuario_id=dona.id, titulo="Da Bia")
    db.add(alheia)
    db.commit()

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        ws.send_json({"tipo": "chat.parar", "conversa_id": alheia.id})

        assert ws.receive_json()["code"] == "conversa_nao_encontrada"


# --- falhas -------------------------------------------------------------------------------


def test_ia_fora_antes_de_responder_nao_grava_nada(
    cliente: TestClient, token: str, provedor: ProvedorFalso, sessao_factory: sessionmaker[Session]
) -> None:
    provedor.falhar_antes = True

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        perguntar(ws)
        erro = ws.receive_json()

    assert (erro["tipo"], erro["code"]) == ("erro", "ia_indisponivel")
    with sessao_factory() as db:
        assert db.scalars(select(Conversa)).all() == []


def test_ia_que_cai_no_meio_grava_o_parcial(
    cliente: TestClient, token: str, provedor: ProvedorFalso, sessao_factory: sessionmaker[Session]
) -> None:
    provedor.falhar_depois_de = 2

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        perguntar(ws)
        recebidas = ate(ws, "chat.erro")

    assert recebidas[-1]["payload"]["code"] == "ia_indisponivel"
    [resposta] = respostas(sessao_factory)
    assert (resposta.conteudo, resposta.incompleta) == ("Olá, ", True)


def test_aba_que_fecha_no_meio_deixa_o_parcial_gravado(
    cliente: TestClient, token: str, provedor: ProvedorFalso, sessao_factory: sessionmaker[Session]
) -> None:
    provedor.sem_fim = True
    provedor.pausa = 0.02

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        perguntar(ws)
        ws.receive_json()
        ws.receive_json()
        ws.receive_json()

    for _ in range(100):
        gravadas = respostas(sessao_factory)
        if gravadas:
            break
        time.sleep(0.05)
    assert gravadas and gravadas[0].incompleta is True


def test_conversa_de_outro_aluno_e_ocupada(
    cliente: TestClient, token: str, provedor: ProvedorFalso, db: Session, usuario: Usuario
) -> None:
    dona = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(dona)
    db.commit()
    alheia = Conversa(usuario_id=dona.id, titulo="Da Bia")
    minha = Conversa(usuario_id=usuario.id, titulo="Minha")
    db.add_all([alheia, minha])
    db.commit()
    provedor.sem_fim = True
    provedor.pausa = 0.02

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        perguntar(ws, conversa_id=alheia.id)
        assert ws.receive_json()["code"] == "conversa_nao_encontrada"

        ws.send_json({"tipo": "inscrever", "canal": f"chat:{minha.id}"})
        ws.receive_json()
        perguntar(ws, conversa_id=minha.id)
        assert ws.receive_json()["evento"] == "chat.conversa"
        perguntar(ws, "outra", conversa_id=minha.id)
        recebidas = ate(ws, "nenhum")

        assert recebidas[-1]["code"] == "chat_ocupado"
        ws.send_json({"tipo": "chat.parar", "conversa_id": minha.id})
        ate(ws, "chat.parado")

    assert not chat_ao_vivo.em_andamento(minha.id)
