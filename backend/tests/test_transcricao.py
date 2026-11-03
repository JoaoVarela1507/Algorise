"""Transcrição dos vídeos do YouTube para o vault (#208).

O `yt-dlp` e o Whisper só existem na imagem do worker: aqui eles são trocados
por funções do teste, e o que se confere é o caminho em volta deles (a legenda
antes do áudio, a pasta apagada, o vault, as falhas).
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import fakeredis
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.fila import FilaRedis
from app.ia.eco import Eco
from app.ia.vault import buscar
from app.ia.vault.trechos import Fala
from app.models import DocumentoVault, StatusVideo, VideoYoutube
from app.services import transcricao
from app.tarefas import transcricao as tarefa

VTT = """WEBVTT

00:00.000 --> 00:04.000
Um laço repete um bloco de código.

00:04.000 --> 00:09.500
O while repete enquanto a condição for verdadeira.
"""

FALAS = [
    Fala("Uma função recebe parâmetros.", 0.0, 3.5),
    Fala("E devolve um valor com return.", 3.5, 7.0),
]


@pytest.fixture
def video(db: Session) -> VideoYoutube:
    registro = VideoYoutube(youtube_id="abc123", titulo="Funções em Python", duracao_segundos=600)
    db.add(registro)
    db.commit()
    return registro


@pytest.fixture
def segmentacoes(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Os vídeos que a transcrição pôs na fila da segmentação (#209)."""
    enfileirados: list[int] = []

    class Espia:
        def segmentacao(self, video_id: int) -> bool:
            enfileirados.append(video_id)
            return True

    monkeypatch.setattr(tarefa, "fila_das_tarefas", Espia)
    return enfileirados


@pytest.fixture
def no_worker(sessao_factory, segmentacoes: list[int], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tarefa, "SessionLocal", sessao_factory)
    monkeypatch.setattr(tarefa, "get_provedor_ia_tarefas", Eco)


@pytest.fixture
def pastas(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """As pastas temporárias que a tarefa usou, para conferir que sumiram."""
    usadas: list[Path] = []

    def falas_do_video(youtube_id: str, pasta: Path) -> tuple[list[Fala], str]:
        usadas.append(pasta)
        (pasta / f"{youtube_id}.webm").write_bytes(b"audio")
        return FALAS, "whisper"

    monkeypatch.setattr(transcricao, "falas_do_video", falas_do_video)
    return usadas


# --- de onde vêm as falas -----------------------------------------------------------------


def test_legenda_manual_vem_antes_do_audio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def baixar_legenda(youtube_id: str, pasta: Path) -> Path:
        arquivo = pasta / f"{youtube_id}.pt.vtt"
        arquivo.write_text(VTT, encoding="utf-8")
        return arquivo

    def nao_deveria_baixar(*_args: object) -> Path:
        raise AssertionError("baixou o áudio tendo legenda")

    monkeypatch.setattr(transcricao, "baixar_legenda", baixar_legenda)
    monkeypatch.setattr(transcricao, "baixar_audio", nao_deveria_baixar)

    falas, fonte = transcricao.falas_do_video("abc123", tmp_path)

    assert fonte == "legenda"
    assert falas[1] == Fala("O while repete enquanto a condição for verdadeira.", 4.0, 9.5)


@pytest.mark.parametrize("legenda", [None, "WEBVTT\n\n"])
def test_sem_legenda_ou_legenda_vazia_o_whisper_transcreve_o_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, legenda: str | None
) -> None:
    def baixar_legenda(youtube_id: str, pasta: Path) -> Path | None:
        if legenda is None:
            return None
        arquivo = pasta / "vazia.vtt"
        arquivo.write_text(legenda, encoding="utf-8")
        return arquivo

    monkeypatch.setattr(transcricao, "baixar_legenda", baixar_legenda)
    monkeypatch.setattr(transcricao, "baixar_audio", lambda youtube_id, pasta: pasta / "a.webm")
    monkeypatch.setattr(transcricao, "transcrever_audio", lambda caminho: FALAS)

    assert transcricao.falas_do_video("abc123", tmp_path) == (FALAS, "whisper")


# --- a tarefa -----------------------------------------------------------------------------


def test_video_transcrito_vai_para_o_vault_com_inicio_e_fim(
    db: Session, video: VideoYoutube, no_worker: None, pastas: list[Path], segmentacoes: list[int]
) -> None:
    """O critério da #208: trechos com início e fim, e nada baixado fica no disco."""
    tarefa.transcrever(video.id)

    db.expire_all()
    assert db.get(VideoYoutube, video.id).status is StatusVideo.transcrito
    documento = db.scalars(select(DocumentoVault)).one()
    assert (documento.chave, documento.video_id, documento.modulo_id) == (
        "youtube:abc123",
        video.id,
        None,
    )
    [trecho] = documento.trechos
    assert (trecho.inicio_segundos, trecho.fim_segundos) == (0.0, 7.0)
    assert [pasta.exists() for pasta in pastas] == [False]
    # O próximo passo, as partes do vídeo, foi para a fila.
    assert segmentacoes == [video.id]


def test_busca_no_vault_acha_o_video_ainda_sem_modulo(
    db: Session, video: VideoYoutube, no_worker: None, pastas: list[Path]
) -> None:
    tarefa.transcrever(video.id)

    [resultado] = asyncio.run(buscar(db, Eco(), "o que o return devolve da função?", limite=1))

    assert (resultado.video_id, resultado.modulo_id, resultado.fim_segundos) == (
        video.id,
        None,
        7.0,
    )


def test_video_longo_demais_nem_e_baixado(
    db: Session, video: VideoYoutube, no_worker: None, pastas: list[Path], monkeypatch
) -> None:
    monkeypatch.setattr(settings, "transcricao_duracao_maxima", 300)

    tarefa.transcrever(video.id)

    db.expire_all()
    registro = db.get(VideoYoutube, video.id)
    assert (registro.status, registro.erro) == (
        StatusVideo.falhou,
        "Vídeo longo demais para transcrever.",
    )
    assert pastas == []


def test_video_indisponivel_grava_o_motivo_e_apaga_a_pasta(
    db: Session, video: VideoYoutube, no_worker: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    usadas: list[Path] = []

    def privado(youtube_id: str, pasta: Path) -> tuple[list[Fala], str]:
        usadas.append(pasta)
        (pasta / "pedaco.part").write_bytes(b"x")
        raise transcricao.VideoIndisponivel("Private video")

    monkeypatch.setattr(transcricao, "falas_do_video", privado)

    tarefa.transcrever(video.id)

    db.expire_all()
    registro = db.get(VideoYoutube, video.id)
    assert (registro.status, registro.erro) == (
        StatusVideo.falhou,
        "Vídeo indisponível: Private video",
    )
    assert not usadas[0].exists()


def test_erro_inesperado_estoura_para_a_fila_tentar_de_novo(
    db: Session, video: VideoYoutube, no_worker: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    usadas: list[Path] = []

    def quebra(youtube_id: str, pasta: Path) -> tuple[list[Fala], str]:
        usadas.append(pasta)
        raise RuntimeError("o Whisper ficou sem memória")

    monkeypatch.setattr(transcricao, "falas_do_video", quebra)

    with pytest.raises(RuntimeError):
        tarefa.transcrever(video.id)

    assert not usadas[0].exists()
    # Depois da última tentativa, o callback da fila grava a falha.
    tarefa.falhou(SimpleNamespace(args=[video.id], retries_left=0), None, RuntimeError, None, None)
    db.expire_all()
    registro = db.get(VideoYoutube, video.id)
    assert (registro.status, registro.erro) == (StatusVideo.falhou, tarefa.ERRO_INESPERADO)


def test_callback_com_tentativa_sobrando_nao_marca_falha(
    db: Session, video: VideoYoutube, no_worker: None
) -> None:
    tarefa.falhou(SimpleNamespace(args=[video.id], retries_left=1), None, RuntimeError, None, None)

    db.expire_all()
    assert db.get(VideoYoutube, video.id).status is StatusVideo.aguardando


def test_video_ja_transcrito_nao_e_baixado_de_novo(
    db: Session, video: VideoYoutube, no_worker: None, pastas: list[Path]
) -> None:
    video.status = StatusVideo.transcrito
    db.commit()

    tarefa.transcrever(video.id)

    assert pastas == []


def test_transcricao_entra_na_fila_uma_vez_por_video() -> None:
    fila = FilaRedis(fakeredis.FakeRedis(), "teste")

    assert fila.transcricao(5) is True
    assert fila.transcricao(5) is False

    assert fila.fila.job_ids == ["video-5"]


def test_motivo_do_yt_dlp_sai_sem_o_prefixo() -> None:
    erro = Exception("ERROR: [youtube] abc123: Video unavailable. This video is private")

    assert transcricao._motivo(erro) == "Video unavailable. This video is private"
