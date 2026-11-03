"""Transcrição de um vídeo do YouTube para o vault (#208), executada pelo worker."""

import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from rq.job import Job
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.ia import get_provedor_ia_tarefas
from app.ia.vault import ingerir_video
from app.models import StatusVideo, VideoYoutube
from app.services import transcricao

logger = logging.getLogger(__name__)

ERRO_INESPERADO = "A transcrição falhou de um jeito inesperado."


def transcrever(video_id: int) -> None:
    """Baixa a legenda ou o áudio, transcreve, grava no vault e apaga o que baixou.

    A falha esperada (vídeo privado, longo demais) fica no vídeo, com o motivo,
    e a tarefa termina sem erro. O resto estoura, e a fila tenta de novo.
    """
    with SessionLocal() as db:
        video = db.get(VideoYoutube, video_id)
        if video is None or video.status is StatusVideo.transcrito:
            return
        if (video.duracao_segundos or 0) > settings.transcricao_duracao_maxima:
            _falhar(db, video, "Vídeo longo demais para transcrever.")
            return

        video.status = StatusVideo.transcrevendo
        video.erro = None
        db.commit()

        # Apagada no fim, com sucesso ou com falha: o áudio não fica no disco.
        with TemporaryDirectory(prefix="algorise-video-") as pasta:
            try:
                falas, fonte = transcricao.falas_do_video(video.youtube_id, Path(pasta))
            except transcricao.VideoIndisponivel as erro:
                _falhar(db, video, f"Vídeo indisponível: {erro}")
                return
        if not falas:
            _falhar(db, video, "O vídeo não tem fala para transcrever.")
            return

        asyncio.run(ingerir_video(db, get_provedor_ia_tarefas(), video, falas))
        video.status = StatusVideo.transcrito
        db.commit()
        logger.info("Vídeo %s transcrito pela %s: %d falas", video.youtube_id, fonte, len(falas))


def falhou(job: Job, connection: object, tipo: type, valor: BaseException, tb: object) -> None:
    """Callback do RQ: a tarefa estourou em todas as tentativas."""
    if job.retries_left:
        return
    with SessionLocal() as db:
        video = db.get(VideoYoutube, job.args[0])
        if video is not None and video.status is not StatusVideo.transcrito:
            logger.error("A transcrição do vídeo %s falhou de vez: %s", video.youtube_id, valor)
            _falhar(db, video, ERRO_INESPERADO)


def _falhar(db: Session, video: VideoYoutube, motivo: str) -> None:
    video.status = StatusVideo.falhou
    video.erro = motivo
    db.commit()
