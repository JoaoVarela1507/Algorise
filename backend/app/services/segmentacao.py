"""Partes de um vídeo transcrito, para virarem módulos da trilha (#209).

O vídeo curto, o caso comum nas playlists, vira uma parte só, sem chamar a IA.
O longo vai para a skill `segmentar_video` com o índice da transcrição do vault;
a resposta é ajustada às fronteiras de fala e, se não validar, o vídeo é cortado
por duração. A IA fora do ar estoura: a fila tenta de novo mais tarde.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ia import ProvedorIA
from app.ia.skills import segmentar_video
from app.ia.vault.trechos import Trecho
from app.models import DocumentoVault, ParteVideo, VideoYoutube

logger = logging.getLogger(__name__)


async def segmentar(db: Session, provedor: ProvedorIA, video: VideoYoutube) -> list[ParteVideo]:
    """Grava as partes do vídeo, substituindo as que houvesse. Devolve as partes."""
    trechos = _trechos(db, video)
    duracao = float(video.duracao_segundos or (trechos[-1].fim if trechos else 0) or 0)
    fronteiras = [t.inicio for t in trechos if t.inicio is not None]
    maximo = settings.segmentacao_duracao_maxima

    if duracao <= maximo or not trechos:
        partes = [segmentar_video.Parte(inicio=0, fim=max(duracao, 1), titulo=video.titulo[:120])]
    else:
        try:
            partes = await _pela_ia(provedor, video, trechos, fronteiras, duracao)
        except segmentar_video.SaidaInvalida:
            logger.warning(
                "Segmentação inválida do vídeo %s; cortando por duração", video.youtube_id
            )
            partes = segmentar_video.por_duracao(
                video.titulo, fronteiras, duracao, maximo_segundos=maximo
            )

    video.partes.clear()
    db.flush()
    video.partes = [
        ParteVideo(
            ordem=i,
            inicio_segundos=parte.inicio,
            fim_segundos=parte.fim,
            titulo=parte.titulo[:200],
            resumo=parte.resumo or None,
        )
        for i, parte in enumerate(partes)
    ]
    db.commit()
    return video.partes


async def _pela_ia(
    provedor: ProvedorIA,
    video: VideoYoutube,
    trechos: list[Trecho],
    fronteiras: list[float],
    duracao: float,
) -> list[segmentar_video.Parte]:
    pedacos = [
        pedaco
        async for pedaco in provedor.gerar(
            segmentar_video.mensagens(
                video.titulo,
                trechos,
                maximo_minutos=settings.segmentacao_duracao_maxima // 60,
            ),
            max_tokens=segmentar_video.MAXIMO_DE_TOKENS,
            formato=segmentar_video.FORMATO,
        )
    ]
    resposta = segmentar_video.ler_resposta("".join(pedacos))
    return segmentar_video.ajustar(resposta.partes, fronteiras, duracao)


def _trechos(db: Session, video: VideoYoutube) -> list[Trecho]:
    documento = db.scalar(select(DocumentoVault).where(DocumentoVault.video_id == video.id))
    if documento is None:
        return []
    return [
        Trecho(t.texto, t.inicio_segundos, t.fim_segundos)
        for t in documento.trechos
        if t.inicio_segundos is not None
    ]
