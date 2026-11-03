"""Execução do código do desafio na sandbox (#34), pelo worker."""

from rq.job import Job
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.services import desafios


def executar(execucao_id: str) -> None:
    executar_com(SessionLocal, execucao_id)


def executar_com(fabrica: sessionmaker[Session], execucao_id: str) -> None:
    """Com a sessão dada: a do worker, ou a do request no modo `local`."""
    with fabrica() as db:
        desafios.executar(db, execucao_id)


def falhou(job: Job, connection: object, tipo: type, valor: BaseException, tb: object) -> None:
    """O RQ desistiu do job (timeout, worker derrubado): a execução não fica presa."""
    with SessionLocal() as db:
        desafios.falhar(db, str(job.args[0]), "A execução não terminou a tempo.")
