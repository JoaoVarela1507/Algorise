"""Fila do trabalho longo (#206): o RQ sobre o Redis e o worker fora da API.

O Redis é o `fakeredis`, e o worker é o `SimpleWorker` do RQ, que roda a tarefa
no próprio processo, sem fork (que o Windows não tem), em modo burst: processa o
que está na fila e para.
"""

from collections.abc import Iterator
from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from rq import Queue, SimpleWorker
from rq.job import Job
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.fila import FilaRedis, get_fila
from app.ia.eco import Eco
from app.main import app
from app.models import Ementa, StatusEmenta
from app.tarefas import ementa as tarefa
from tests.test_onboarding import TEXTO_DA_EMENTA, pdf_com_texto


@pytest.fixture
def conexao() -> fakeredis.FakeRedis:
    # Sem `decode_responses`: o RQ guarda bytes.
    return fakeredis.FakeRedis()


@pytest.fixture
def fila(conexao: fakeredis.FakeRedis) -> FilaRedis:
    return FilaRedis(conexao, "teste")


@pytest.fixture
def no_worker(sessao_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    """O worker usa a sessão e o provedor dele; aqui, os do teste."""
    monkeypatch.setattr(tarefa, "SessionLocal", sessao_factory)
    monkeypatch.setattr(tarefa, "get_provedor_ia_tarefas", Eco)


@pytest.fixture
def midia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "diretorio_midia", str(tmp_path))
    return tmp_path


@pytest.fixture
def com_fila_redis(cliente: TestClient, fila: FilaRedis) -> Iterator[FilaRedis]:
    app.dependency_overrides[get_fila] = lambda: fila
    yield fila
    app.dependency_overrides.pop(get_fila, None)


def rodar_worker(conexao: fakeredis.FakeRedis) -> None:
    SimpleWorker([Queue("teste", connection=conexao)], connection=conexao).work(burst=True)


def test_ementa_enviada_vai_para_a_fila_e_o_worker_a_processa(
    cliente: TestClient,
    autenticado: dict[str, str],
    com_fila_redis: FilaRedis,
    conexao: fakeredis.FakeRedis,
    no_worker: None,
    midia: Path,
    db: Session,
) -> None:
    """O critério da #206: a API só enfileira, e quem lê o PDF é o worker."""
    resposta = cliente.post(
        "/api/v1/ementas",
        headers=autenticado,
        files={"arquivo": ("ementa.pdf", pdf_com_texto(TEXTO_DA_EMENTA), "application/pdf")},
    )
    ementa_id = resposta.json()["id"]

    # Respondida a requisição, nada foi lido ainda: a tarefa está na fila.
    assert resposta.status_code == 202
    assert db.get(Ementa, ementa_id).status is StatusEmenta.pendente
    assert Queue("teste", connection=conexao).job_ids == [f"ementa-{ementa_id}"]

    rodar_worker(conexao)

    db.expire_all()
    ementa = db.get(Ementa, ementa_id)
    assert ementa.status is StatusEmenta.processada
    assert "Conteudo programatico" in ementa.texto_extraido


def test_mesma_ementa_pendente_nao_entra_duas_vezes(fila: FilaRedis) -> None:
    assert fila.ementa(7) is True
    assert fila.ementa(7) is False
    assert fila.ementa(8) is True

    assert fila.fila.job_ids == ["ementa-7", "ementa-8"]


def test_ementa_ja_processada_pode_voltar_para_a_fila(
    fila: FilaRedis, conexao: fakeredis.FakeRedis, no_worker: None
) -> None:
    """Terminada a tarefa, a chave fica livre: é a releitura dos assuntos."""
    fila.ementa(99)
    rodar_worker(conexao)

    assert fila.ementa(99) is True


def test_tarefa_tem_tempo_maximo_e_novas_tentativas(fila: FilaRedis) -> None:
    fila.ementa(3)

    tarefa = Job.fetch("ementa-3", connection=fila.fila.connection)
    assert tarefa.timeout == 2 * 60 * 60
    assert tarefa.retries_left == 2
    assert tarefa.func_name == "app.tarefas.ementa.processar"


def test_falha_definitiva_grava_o_motivo_na_ementa(
    fila: FilaRedis,
    conexao: fakeredis.FakeRedis,
    no_worker: None,
    db: Session,
    usuario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O worker que estoura em todas as tentativas não deixa a ementa em `processando`."""
    ementa = Ementa(usuario_id=usuario.id, arquivo_path="x.pdf", status=StatusEmenta.processando)
    db.add(ementa)
    db.commit()

    def estourar(*_args: object) -> None:
        raise RuntimeError("o banco sumiu")

    monkeypatch.setattr(tarefa.ementas, "processar", estourar)
    # Sem espera entre as tentativas, para o burst fazer as três de uma vez.
    monkeypatch.setattr("app.core.fila.NOVAS_TENTATIVAS.intervals", [0])
    fila.ementa(ementa.id)

    for _ in range(3):
        rodar_worker(conexao)

    db.expire_all()
    ementa = db.get(Ementa, ementa.id)
    assert (ementa.status, ementa.erro) == (StatusEmenta.falhou, tarefa.ERRO_INESPERADO)


def test_producao_exige_a_fila_no_redis() -> None:
    segredo = "s" * 40
    with pytest.raises(ValidationError, match="FILA"):
        Settings(environment="production", jwt_secret=segredo)
    with pytest.raises(ValidationError, match="FILA"):
        Settings(fila="celery")
    assert Settings(environment="production", jwt_secret=segredo, fila="redis").fila == "redis"
