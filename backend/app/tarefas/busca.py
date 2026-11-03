"""Busca de vídeos para as lacunas de uma disciplina (#207), executada pelo worker."""

import asyncio
import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.ia import get_provedor_ia_tarefas
from app.services import busca_conteudo
from app.services.youtube import ClienteYoutube

logger = logging.getLogger(__name__)


def buscar(disciplina: str) -> None:
    """Sem `YOUTUBE_API_KEY`, não faz nada: as lacunas esperam em `pendente`."""
    if not settings.youtube_api_key:
        logger.info("Busca de %s ignorada: YOUTUBE_API_KEY não definida", disciplina)
        return
    with SessionLocal() as db:
        cliente = ClienteYoutube(db, settings.youtube_api_key)
        resultado = asyncio.run(
            busca_conteudo.buscar(db, cliente, get_provedor_ia_tarefas(), disciplina)
        )
    logger.info(
        "Busca de %s: %d lacunas cobertas, %d sem conteúdo, playlist %s%s",
        disciplina,
        resultado.cobertas,
        resultado.sem_conteudo,
        resultado.playlist_id or "nenhuma",
        " (parou por cota)" if resultado.interrompida else "",
    )
