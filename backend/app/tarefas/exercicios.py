"""Geração dos exercícios de prática de um módulo (#201), executada pelo worker."""

import asyncio

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.ia import ProvedorIA, get_provedor_ia_tarefas
from app.models import ExerciciosGerados, StatusGeracao
from app.services import exercicios


def gerar(geracao_id: int) -> None:
    gerar_com(SessionLocal, get_provedor_ia_tarefas(), geracao_id)


def gerar_com(fabrica: sessionmaker[Session], provedor: ProvedorIA, geracao_id: int) -> None:
    """Com a sessão e o provedor dados: os do worker, ou os do request no modo `local`."""
    with fabrica() as db:
        geracao = db.get(ExerciciosGerados, geracao_id)
        if geracao is None or geracao.status is not StatusGeracao.gerando:
            return
        asyncio.run(exercicios.gerar(db, provedor, geracao))
