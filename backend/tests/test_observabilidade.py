"""Logs estruturados, métricas e auditoria (#39)."""

import json
import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core import auditoria, logs, metricas
from app.core.config import Settings, settings
from tests.conftest import SENHA_VALIDA


class Captura(logging.Handler):
    """Guarda cada linha já formatada em JSON, no momento em que é emitida."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(logs.FormatoJson())
        self.addFilter(logs.FiltroDeSegredos())
        self.linhas: list[dict] = []

    def emit(self, registro: logging.LogRecord) -> None:
        self.linhas.append(json.loads(self.format(registro)))


@pytest.fixture
def captura() -> Iterator[Captura]:
    handler = Captura()
    raiz = logging.getLogger()
    nivel = raiz.level
    raiz.addHandler(handler)
    raiz.setLevel(logging.INFO)
    yield handler
    raiz.removeHandler(handler)
    raiz.setLevel(nivel)


def linhas_de(captura: Captura, logger: str) -> list[dict]:
    return [linha for linha in captura.linhas if linha["logger"] == logger]


# --- logs ---------------------------------------------------------------------------------


def test_linha_da_requisicao_tem_request_id_rota_e_aluno(
    cliente: TestClient, autenticado: dict[str, str], captura: Captura, usuario
) -> None:
    resposta = cliente.get(
        "/api/v1/usuarios/me", headers={**autenticado, "X-Request-Id": "req-123"}
    )

    [linha] = [
        linha
        for linha in linhas_de(captura, "app.requisicao")
        if linha.get("rota") == "/api/v1/usuarios/me"
    ]
    assert resposta.status_code == 200
    assert linha["request_id"] == "req-123"
    assert (linha["metodo"], linha["status"], linha["aluno_id"]) == ("GET", 200, usuario.id)
    assert linha["modelo_da_rota"] == "/api/v1/usuarios/me"
    assert isinstance(linha["duracao_ms"], int)


def test_token_senha_e_conteudo_do_chat_nunca_vao_para_o_log(captura: Captura) -> None:
    logger = logging.getLogger("app.teste")
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.assinatura"

    logger.info("cabeçalho Authorization: Bearer %s", "abc.def.ghi")
    logger.info("token no texto: %s", jwt)
    logger.info("cadastro", extra={"senha": "Trilha-Boa-2026", "conteudo": "minha dúvida"})

    textos = json.dumps(captura.linhas, ensure_ascii=False)
    assert "abc.def.ghi" not in textos
    assert jwt not in textos
    assert "Trilha-Boa-2026" not in textos
    assert "minha dúvida" not in textos
    assert captura.linhas[0]["mensagem"] == "cabeçalho Authorization: Bearer [apagado]"
    assert captura.linhas[2]["senha"] == logs.APAGADO


def test_excecao_sai_com_o_stack_trace(captura: Captura) -> None:
    try:
        raise ValueError("quebrou")
    except ValueError:
        logging.getLogger("app.teste").exception("falha inesperada")

    assert "ValueError: quebrou" in captura.linhas[0]["erro"]


def test_formato_padrao_e_json_em_producao() -> None:
    segredo = "s" * 40
    producao = Settings(environment="production", jwt_secret=segredo, fila="redis")

    assert (producao.formato_de_log, Settings().formato_de_log) == ("json", "texto")
    with pytest.raises(ValueError, match="LOG_FORMATO"):
        Settings(log_formato="xml")


# --- auditoria ----------------------------------------------------------------------------


def test_login_certo_e_errado_vao_para_a_auditoria(
    cliente: TestClient, usuario, captura: Captura
) -> None:
    cliente.post("/api/v1/auth/login", json={"email": usuario.email, "senha": "errada-123"})
    cliente.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA_VALIDA})

    eventos = [
        (linha["evento"], linha.get("alvo_usuario_id"), linha.get("email"))
        for linha in linhas_de(captura, "app.auditoria")
    ]
    assert eventos == [("login_falhou", None, "an***@ufrpe.br"), ("login", usuario.id, None)]


def test_exclusao_de_conta_vai_para_a_auditoria(
    cliente: TestClient, autenticado: dict[str, str], usuario, captura: Captura
) -> None:
    cliente.request(
        "DELETE",
        "/api/v1/usuarios/me",
        headers=autenticado,
        json={"confirmacao": "EXCLUIR", "senha": SENHA_VALIDA},
    )

    [evento] = [
        linha
        for linha in linhas_de(captura, "app.auditoria")
        if linha["evento"] == "exclusao_agendada"
    ]
    assert evento["alvo_usuario_id"] == usuario.id


def test_email_parcial() -> None:
    assert auditoria.email_parcial("ana.lima@ufrpe.br") == "an***@ufrpe.br"
    assert auditoria.email_parcial("sem-arroba") == "***"


# --- métricas -----------------------------------------------------------------------------


def test_metricas_contam_requisicoes_pelo_modelo_da_rota(
    cliente: TestClient, autenticado: dict[str, str], trilha
) -> None:
    cliente.get(f"/api/v1/trilhas/{trilha.slug}", headers=autenticado)

    corpo = cliente.get("/metrics").text

    assert 'algorise_requisicoes_segundos_count{metodo="GET",rota="/api/v1/trilhas/{slug}"' in corpo
    # O slug não vira uma série nova.
    assert f'rota="/api/v1/trilhas/{trilha.slug}"' not in corpo


def test_metricas_pedem_o_token_quando_configurado(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "metricas_token", "segredo-das-metricas")

    sem = cliente.get("/metrics")
    com = cliente.get("/metrics", headers={"Authorization": "Bearer segredo-das-metricas"})

    assert (sem.status_code, com.status_code) == (401, 200)


def test_tempo_da_ia_fica_na_metrica_mesmo_com_erro() -> None:
    antes = metricas.ia.labels("teste", "erro")._sum.get()

    with pytest.raises(RuntimeError), metricas.medir_ia("teste"):
        raise RuntimeError("fora")

    assert metricas.ia.labels("teste", "erro")._sum.get() >= antes


def test_fila_entra_na_metrica_so_com_o_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    import fakeredis
    from rq import Queue

    conexao = fakeredis.FakeRedis()
    Queue("algorise", connection=conexao).enqueue("app.tarefas.ementa.processar", 1)
    monkeypatch.setattr(settings, "fila", "redis")
    monkeypatch.setattr("app.core.fila.conexao", lambda: conexao)

    [metrica] = list(metricas.ColetorDaFila().collect())

    assert metrica.samples[0].value == 1
    monkeypatch.setattr(settings, "fila", "local")
    assert list(metricas.ColetorDaFila().collect()) == []
