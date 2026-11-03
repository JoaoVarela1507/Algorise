"""Segmentação de um vídeo transcrito em partes (#209), executada pelo worker."""

import asyncio
import logging

from app.core.database import SessionLocal
from app.ia import get_provedor_ia_tarefas
from app.models import StatusVideo, VideoYoutube
from app.services import segmentacao

logger = logging.getLogger(__name__)


def segmentar(video_id: int) -> None:
    """Só o vídeo já transcrito: as partes saem do índice da transcrição."""
    with SessionLocal() as db:
        video = db.get(VideoYoutube, video_id)
        if video is None or video.status is not StatusVideo.transcrito:
            return
        partes = asyncio.run(segmentacao.segmentar(db, get_provedor_ia_tarefas(), video))
        logger.info("Vídeo %s em %d partes", video.youtube_id, len(partes))
