"""Gateway de WebSocket (#35): autenticação, canais, pub/sub e os limites.

O pub/sub roda no `fakeredis`, que tem `PUBLISH` e `PSUBSCRIBE` de verdade. A
"outra instância da API" dos testes de pub/sub é um segundo `Gerenciador` com o
seu `Ouvinte`, ligado ao mesmo Redis.
"""

import threading
from collections.abc import Iterator
from typing import Any

import fakeredis
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.testclient import WebSocketTestSession

from app.core.config import settings
from app.core.seguranca import _criar_token, criar_access_token
from app.models import Conversa, Trilha, Usuario
from app.services import tempo_real
from app.services.tempo_real import Gerenciador, LimiteDeMensagens, Ouvinte, publicar

URL = "/api/v1/ws"


@pytest.fixture(autouse=True)
def ouvinte_limpo() -> Iterator[None]:
    """Cada teste começa sem a thread do teste anterior, presa ao Redis dele."""
    tempo_real.ouvinte.parar()
    yield
    tempo_real.ouvinte.parar()


@pytest.fixture
def token(usuario: Usuario) -> str:
    return criar_access_token(usuario.id)


@pytest.fixture
def outro(db: Session) -> Usuario:
    registro = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(registro)
    db.commit()
    return registro


def entrar(ws: WebSocketTestSession, token: str) -> dict[str, Any]:
    ws.send_json({"tipo": "autenticar", "token": token})
    return ws.receive_json()


def inscrever(ws: WebSocketTestSession, canal: str) -> dict[str, Any]:
    ws.send_json({"tipo": "inscrever", "canal": canal})
    return ws.receive_json()


def fechamento(ws: WebSocketTestSession) -> int:
    with pytest.raises(WebSocketDisconnect) as fechou:
        while True:
            ws.receive_json()
    return fechou.value.code


def esperar_ouvinte() -> None:
    assert tempo_real.ouvinte.inscrito.wait(timeout=5), "o ouvinte não se inscreveu no Redis"


# --- autenticação -------------------------------------------------------------------------


def test_autentica_pelo_primeiro_frame(cliente: TestClient, token: str, usuario: Usuario) -> None:
    with cliente.websocket_connect(URL) as ws:
        assert entrar(ws, token) == {"tipo": "autenticado", "usuario_id": usuario.id}


def test_token_invalido_fecha_com_4401(cliente: TestClient) -> None:
    with cliente.websocket_connect(URL) as ws:
        resposta = entrar(ws, "nao-e-um-jwt")

        assert (resposta["tipo"], resposta["code"]) == ("erro", "nao_autenticado")
        assert fechamento(ws) == 4401


def test_primeiro_frame_que_nao_autentica_fecha(cliente: TestClient) -> None:
    with cliente.websocket_connect(URL) as ws:
        ws.send_json({"tipo": "inscrever", "canal": "ranking:geral"})

        assert ws.receive_json()["code"] == "nao_autenticado"
        assert fechamento(ws) == 4401


def test_sem_autenticar_no_prazo_fecha(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ws_tempo_para_autenticar", 0.2)

    with cliente.websocket_connect(URL) as ws:
        assert ws.receive_json()["code"] == "nao_autenticado"
        assert fechamento(ws) == 4401


def test_token_que_vence_derruba_a_conexao(
    cliente: TestClient, usuario: Usuario, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ws_intervalo_ping", 0.2)
    curto = _criar_token(usuario.id, tipo="access", validade=1)

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, curto)
        recebidas = []
        with pytest.raises(WebSocketDisconnect) as fechou:
            while True:
                recebidas.append(ws.receive_json())

    assert fechou.value.code == 4401
    assert recebidas[-1]["code"] == "token_expirado"


def test_refresh_token_nao_serve(cliente: TestClient, usuario: Usuario) -> None:
    refresh = _criar_token(usuario.id, tipo="refresh", validade=60, jti="x")

    with cliente.websocket_connect(URL) as ws:
        assert entrar(ws, refresh)["code"] == "nao_autenticado"


# --- canais -------------------------------------------------------------------------------


def test_inscricao_nos_canais_permitidos(
    cliente: TestClient, token: str, usuario: Usuario, db: Session
) -> None:
    trilha = Trilha(slug="py", nome="Python", disciplina="Algoritmos", publicada=True)
    conversa = Conversa(usuario_id=usuario.id, titulo="Laços")
    db.add_all([trilha, conversa])
    db.commit()

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        for canal in (
            f"notificacoes:{usuario.id}",
            "ranking:geral",
            f"ranking:{trilha.id}",
            f"chat:{conversa.id}",
        ):
            assert inscrever(ws, canal) == {"tipo": "inscrito", "canal": canal}
        ws.send_json({"tipo": "cancelar", "canal": "ranking:geral"})
        assert ws.receive_json() == {"tipo": "cancelado", "canal": "ranking:geral"}


def test_canais_de_outro_aluno_sao_negados(
    cliente: TestClient, token: str, outro: Usuario, db: Session
) -> None:
    alheia = Conversa(usuario_id=outro.id, titulo="Da Bia")
    db.add(alheia)
    db.commit()

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        for canal in (
            f"notificacoes:{outro.id}",
            f"chat:{alheia.id}",
            "ranking:9999",
            "desconhecido:1",
        ):
            assert inscrever(ws, canal)["code"] == "canal_negado"


def test_ping_pong_e_mensagem_fora_do_contrato(cliente: TestClient, token: str) -> None:
    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        ws.send_json({"tipo": "ping"})
        assert ws.receive_json() == {"tipo": "pong"}
        ws.send_json({"tipo": "inventado"})
        assert ws.receive_json()["code"] == "mensagem_invalida"
        ws.send_text("isso não é JSON")
        assert ws.receive_json()["code"] == "mensagem_invalida"


# --- entrega ------------------------------------------------------------------------------


def test_duas_abas_recebem_o_mesmo_evento(
    cliente: TestClient, token: str, usuario: Usuario
) -> None:
    canal = f"notificacoes:{usuario.id}"
    with cliente.websocket_connect(URL) as aba1, cliente.websocket_connect(URL) as aba2:
        for aba in (aba1, aba2):
            entrar(aba, token)
            inscrever(aba, canal)
        esperar_ouvinte()

        publicar(canal, "notificacao.nova", {"texto": "Você subiu no ranking"})

        for aba in (aba1, aba2):
            assert aba.receive_json() == {
                "tipo": "evento",
                "canal": canal,
                "evento": "notificacao.nova",
                "payload": {"texto": "Você subiu no ranking"},
            }


def test_evento_de_um_canal_nao_vaza_para_outro(
    cliente: TestClient, token: str, usuario: Usuario
) -> None:
    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        inscrever(ws, "ranking:geral")
        esperar_ouvinte()

        publicar(f"notificacoes:{usuario.id}", "x")
        publicar("ranking:geral", "ranking.atualizado")

        assert ws.receive_json()["evento"] == "ranking.atualizado"


def test_sem_redis_a_entrega_e_local(
    cliente: TestClient, token: str, usuario: Usuario, redis_fora: None
) -> None:
    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        inscrever(ws, "ranking:geral")

        publicar("ranking:geral", "ranking.atualizado", {"xp": 10})

        assert ws.receive_json()["payload"] == {"xp": 10}


class GerenciadorQueAnota(Gerenciador):
    def __init__(self) -> None:
        super().__init__()
        self.recebidas: list[tuple[str, dict[str, Any]]] = []
        self.chegou = threading.Event()

    def entregar_local(self, canal: str, mensagem: dict[str, Any]) -> int:
        self.recebidas.append((canal, mensagem))
        self.chegou.set()
        return 1


def test_evento_publicado_chega_as_outras_instancias(redis_falso: fakeredis.FakeRedis) -> None:
    outra_instancia = GerenciadorQueAnota()
    ouvinte = Ouvinte(outra_instancia)
    ouvinte.garantir()
    try:
        assert ouvinte.inscrito.wait(timeout=5)

        publicar("ranking:geral", "ranking.atualizado")

        assert outra_instancia.chegou.wait(timeout=5)
        assert outra_instancia.recebidas[0][0] == "ranking:geral"
        assert outra_instancia.recebidas[0][1]["evento"] == "ranking.atualizado"
    finally:
        ouvinte.parar()


# --- limites e conexão morta --------------------------------------------------------------


def test_limite_de_abas_por_aluno(
    cliente: TestClient, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ws_conexoes_por_usuario", 1)

    with cliente.websocket_connect(URL) as primeira:
        entrar(primeira, token)
        with cliente.websocket_connect(URL) as segunda:
            assert entrar(segunda, token)["code"] == "conexoes_demais"
            assert fechamento(segunda) == 4429


def test_rate_limit_por_conexao(
    cliente: TestClient, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ws_mensagens_por_janela", 2)
    monkeypatch.setattr(settings, "ws_janela_segundos", 60)

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        respostas = []
        for _ in range(3):
            ws.send_json({"tipo": "ping"})
            respostas.append(ws.receive_json())

    assert [r["tipo"] for r in respostas] == ["pong", "pong", "erro"]
    assert respostas[2]["code"] == "rate_limit"


def test_conexao_calada_e_derrubada(
    cliente: TestClient, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ws_intervalo_ping", 0.05)
    monkeypatch.setattr(settings, "ws_tempo_morto", 0.2)

    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        recebidas = []
        with pytest.raises(WebSocketDisconnect) as fechou:
            while True:
                recebidas.append(ws.receive_json())

    assert fechou.value.code == 4408
    assert {"tipo": "ping"} in recebidas
    assert recebidas[-1]["code"] == "conexao_morta"


def test_aba_fechada_sai_do_gerenciador(cliente: TestClient, token: str, usuario: Usuario) -> None:
    with cliente.websocket_connect(URL) as ws:
        entrar(ws, token)
        ws.send_json({"tipo": "ping"})
        ws.receive_json()
        assert tempo_real.gerenciador.conexoes_de(usuario.id) == 1

    for _ in range(50):
        if tempo_real.gerenciador.conexoes_de(usuario.id) == 0:
            break
        threading.Event().wait(0.05)
    assert tempo_real.gerenciador.conexoes_de(usuario.id) == 0


def test_janela_do_limite_desliza(monkeypatch: pytest.MonkeyPatch) -> None:
    agora = [100.0]
    monkeypatch.setattr(tempo_real.time, "monotonic", lambda: agora[0])
    limite = LimiteDeMensagens(limite=2, janela=10)

    assert [limite.permitir() for _ in range(3)] == [True, True, False]
    agora[0] += 11
    assert limite.permitir() is True
