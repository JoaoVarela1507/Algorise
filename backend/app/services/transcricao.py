"""As falas de um vídeo do YouTube, com o tempo de cada uma (#208).

Duas fontes, da mais barata para a mais cara:

1. **a legenda manual** em português, quando o canal publicou uma: sai em
   segundos e costuma ser melhor que qualquer transcrição automática. A legenda
   gerada pelo YouTube fica de fora: é pior que o Whisper e erra os termos de
   programação;
2. **o áudio, transcrito pelo Whisper** (`faster-whisper`), na CPU do worker.

O vídeo nunca é baixado: só a legenda ou só o áudio, numa pasta temporária que
quem chama apaga no fim (`TemporaryDirectory`), com sucesso ou com falha.

O `yt-dlp` e o `faster-whisper` são pesados e só existem na imagem do worker
(`requirements-transcricao.txt`): são importados dentro das funções, para a API,
a CI e os testes não precisarem deles.

**Termos do YouTube:** baixar o áudio vai contra eles, exceto quando o dono do
vídeo permite, como nos vídeos Creative Commons. Para o projeto acadêmico o
risco foi aceito; antes de qualquer uso comercial, isto precisa ser revisto.
"""

import logging
from functools import cache
from pathlib import Path

from app.core.config import settings
from app.ia.vault.trechos import Fala, ler_transcricao

logger = logging.getLogger(__name__)

IDIOMAS_DA_LEGENDA = ["pt", "pt-BR", "pt-PT"]


class VideoIndisponivel(Exception):
    """O vídeo não pôde ser baixado: privado, removido, restrito. A mensagem vai para o vídeo."""


def falas_do_video(youtube_id: str, pasta: Path) -> tuple[list[Fala], str]:
    """As falas do vídeo e de onde vieram (`legenda` ou `whisper`)."""
    legenda = baixar_legenda(youtube_id, pasta)
    if legenda is not None:
        falas = ler_transcricao(legenda.read_text(encoding="utf-8"), legenda.name)
        if falas:
            return falas, "legenda"
    audio = baixar_audio(youtube_id, pasta)
    return transcrever_audio(audio), "whisper"


def baixar_legenda(youtube_id: str, pasta: Path) -> Path | None:
    """A legenda manual em português, em `.vtt`, ou `None` se o vídeo não tiver."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    opcoes = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": False,
        "subtitleslangs": IDIOMAS_DA_LEGENDA,
        "subtitlesformat": "vtt",
        "outtmpl": str(pasta / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with YoutubeDL(opcoes) as ydl:
            ydl.download([_url(youtube_id)])
    except DownloadError as erro:
        raise VideoIndisponivel(_motivo(erro)) from erro
    return next(iter(sorted(pasta.glob("*.vtt"))), None)


def baixar_audio(youtube_id: str, pasta: Path) -> Path:
    """Só o áudio, no melhor formato que o YouTube der (o Whisper lê qualquer um)."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    opcoes = {
        "format": "bestaudio/best",
        "outtmpl": str(pasta / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(_url(youtube_id), download=True)
            return Path(ydl.prepare_filename(info))
    except DownloadError as erro:
        raise VideoIndisponivel(_motivo(erro)) from erro


def transcrever_audio(caminho: Path) -> list[Fala]:
    """As falas do áudio, com início e fim. O VAD pula os silêncios longos."""
    segmentos, _info = _modelo().transcribe(str(caminho), language="pt", vad_filter=True)
    return [
        Fala(segmento.text.strip(), segmento.start, segmento.end)
        for segmento in segmentos
        if segmento.text.strip()
    ]


@cache
def _modelo():
    """Carregado uma vez por processo do worker: são centenas de MB."""
    from faster_whisper import WhisperModel

    logger.info("Carregando o Whisper %s", settings.whisper_modelo)
    return WhisperModel(
        settings.whisper_modelo, device="cpu", compute_type=settings.whisper_computacao
    )


def _url(youtube_id: str) -> str:
    return f"https://www.youtube.com/watch?v={youtube_id}"


def _motivo(erro: Exception) -> str:
    # O `yt-dlp` começa a mensagem com "ERROR: [youtube] <id>: ".
    return str(erro).split(": ", 2)[-1][:500]
