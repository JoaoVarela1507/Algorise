"""Leitura da ementa que morre com o worker (recriar o container no meio).

O RQ deixa a tarefa em `STARTED` até vencer o prazo dela, de horas. Aqui ela só
conta como viva se o worker que a pegou ainda existe; senão, a ementa vira
`falhou`, com o motivo, e o aluno pode pedir para ler de novo.
"""

from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import Queue, Worker
from rq.job import JobStatus
from sqlalchemy.orm import Session

from app.core.fila import get_fila, tarefa_viva
from app.main import app
from app.models import Ementa, StatusAssuntos, StatusEmenta, Usuario
from app.services import ementas


def tarefa_de_exemplo(ementa_id: int) -> None:  # pragma: no cover - nunca roda
    """Só para enfileirar: os testes não sobem worker."""


@pytest.fixture
def conexao() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


# --- a tarefa está viva? ------------------------------------------------------------------


def test_tarefa_na_fila_esta_viva(conexao: fakeredis.FakeRedis) -> None:
    Queue("algorise", connection=conexao).enqueue(tarefa_de_exemplo, 1, job_id="ementa-1")

    assert tarefa_viva(conexao, "ementa-1")


def test_tarefa_que_nao_existe_nao_esta_viva(conexao: fakeredis.FakeRedis) -> None:
    assert not tarefa_viva(conexao, "ementa-9")


def test_tarefa_rodando_vale_so_com_o_worker_vivo(conexao: fakeredis.FakeRedis) -> None:
    fila = Queue("algorise", connection=conexao)
    tarefa = fila.enqueue(tarefa_de_exemplo, 1, job_id="ementa-1")
    tarefa.worker_name = "worker-recriado"
    tarefa.set_status(JobStatus.STARTED)
    tarefa.save()

    # O worker que a pegou sumiu: a tarefa morreu com ele.
    assert not tarefa_viva(conexao, "ementa-1")

    vivo = Worker([fila], connection=conexao, name="worker-recriado")
    vivo.register_birth()
    assert tarefa_viva(conexao, "ementa-1")


# --- a ementa presa -----------------------------------------------------------------------


@pytest.fixture
def presa(db: Session, usuario: Usuario) -> Ementa:
    ementa = Ementa(
        usuario_id=usuario.id,
        arquivo_path="x.pdf",
        status=StatusEmenta.processada,
        texto_extraido="texto",
        status_assuntos=StatusAssuntos.processando,
    )
    db.add(ementa)
    db.commit()
    return ementa


class FilaSemTarefa:
    """A fila de quem recriou o worker: nenhuma leitura viva."""

    def __init__(self) -> None:
        self.enfileiradas: list[int] = []

    def ementa_em_andamento(self, ementa_id: int) -> bool:
        return False

    def ementa(self, ementa_id: int) -> bool:
        self.enfileiradas.append(ementa_id)
        return True


@pytest.fixture
def sem_tarefa() -> Iterator[FilaSemTarefa]:
    fila = FilaSemTarefa()
    app.dependency_overrides[get_fila] = lambda: fila
    yield fila
    app.dependency_overrides.pop(get_fila, None)


def test_status_de_leitura_morta_vira_falhou(
    cliente: TestClient, autenticado: dict[str, str], presa: Ementa, sem_tarefa: FilaSemTarefa
) -> None:
    corpo = cliente.get(f"/api/v1/ementas/{presa.id}", headers=autenticado).json()

    assert corpo["status_assuntos"] == "falhou"
    assert corpo["erro_assuntos"] == ementas.INTERROMPIDA


def test_ler_de_novo_funciona_depois_da_leitura_morta(
    cliente: TestClient, autenticado: dict[str, str], presa: Ementa, sem_tarefa: FilaSemTarefa
) -> None:
    resposta = cliente.post(f"/api/v1/ementas/{presa.id}/assuntos", headers=autenticado)

    assert resposta.status_code == 202
    assert resposta.json()["status_assuntos"] == "pendente"
    assert sem_tarefa.enfileiradas == [presa.id]


def test_leitura_viva_continua_em_andamento(db: Session, presa: Ementa) -> None:
    assert not ementas.marcar_se_interrompida(db, presa, tarefa_viva=True)
    assert presa.status_assuntos is StatusAssuntos.processando


def test_extracao_morta_tambem_vira_falhou(db: Session, presa: Ementa) -> None:
    presa.status = StatusEmenta.processando
    presa.status_assuntos = StatusAssuntos.pendente
    db.commit()

    assert ementas.marcar_se_interrompida(db, presa, tarefa_viva=False)
    assert (presa.status, presa.erro) == (StatusEmenta.falhou, ementas.INTERROMPIDA)


def test_ementa_pronta_nao_e_tocada(db: Session, presa: Ementa) -> None:
    presa.status_assuntos = StatusAssuntos.prontos
    db.commit()

    assert not ementas.marcar_se_interrompida(db, presa, tarefa_viva=False)
