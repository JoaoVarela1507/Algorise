"""Categorização das partes de um vídeo (#202), executada pelo worker."""

import asyncio
import logging

from app.core.database import SessionLocal
from app.core.fila import fila_das_tarefas
from app.ia import get_provedor_ia_tarefas
from app.models import VideoYoutube
from app.services import categorizacao, modulos_de_videos

logger = logging.getLogger(__name__)


def categorizar(video_id: int) -> None:
    """Categoriza as partes e devolve à busca as lacunas que o vídeo não cobriu."""
    with SessionLocal() as db:
        video = db.get(VideoYoutube, video_id)
        if video is None or not video.partes:
            return
        de_volta = asyncio.run(categorizacao.categorizar(db, get_provedor_ia_tarefas(), video))
        # As partes aprovadas viram módulos e fecham as lacunas (#210).
        modulos_de_videos.publicar(db, video)
        aprovadas = sum(1 for parte in video.partes if parte.aprovada)
        logger.info(
            "Vídeo %s: %d de %d partes aprovadas", video.youtube_id, aprovadas, len(video.partes)
        )
    for disciplina in sorted(de_volta):
        fila_das_tarefas().busca_de_conteudo(disciplina)
