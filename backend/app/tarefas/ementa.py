"""Leitura da ementa, executada pelo worker (`rq worker algorise`) fora da API.

A tarefa recebe só ids: o RQ guarda os argumentos no Redis, e uma sessão do
banco ou um cliente HTTP não atravessam esse caminho. A sessão e o provedor de
IA nascem aqui, no worker.
"""

import logging

from rq.job import Job

from app.core.database import SessionLocal
from app.ia import get_provedor_ia_tarefas
from app.models import Ementa, StatusAssuntos, StatusEmenta
from app.services import ementas

logger = logging.getLogger(__name__)

ERRO_INESPERADO = "Não foi possível ler a ementa agora. Tente de novo mais tarde."


def processar(ementa_id: int) -> None:
    """Extrai o texto da ementa e lê os assuntos (ver `services/ementas.processar`)."""
    ementas.processar(SessionLocal, get_provedor_ia_tarefas(), ementa_id)


def falhou(job: Job, connection: object, tipo: type, valor: BaseException, tb: object) -> None:
    """Callback do RQ quando a tarefa estoura: grava a falha onde o aluno a vê.

    A falha esperada já vira `falhou` dentro de `processar`. Esta é a outra: o
    worker caiu no meio, o banco sumiu. Sem ela, a ementa ficaria em
    `processando` para sempre, com a tela do aluno esperando.
    """
    if job.retries_left:
        # Ainda vai ser tentada de novo.
        return
    ementa_id = job.args[0]
    logger.error("A leitura da ementa %s falhou de vez: %s", ementa_id, valor)
    with SessionLocal() as db:
        ementa = db.get(Ementa, ementa_id)
        if ementa is None:
            return
        if ementa.status in (StatusEmenta.pendente, StatusEmenta.processando):
            ementa.status = StatusEmenta.falhou
            ementa.erro = ERRO_INESPERADO
        elif ementa.status_assuntos in (StatusAssuntos.pendente, StatusAssuntos.processando):
            ementa.status_assuntos = StatusAssuntos.falhou
            ementa.erro_assuntos = ERRO_INESPERADO
        db.commit()
