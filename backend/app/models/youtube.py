"""Conteúdo do YouTube que cobre as lacunas das ementas (#207).

A busca escolhe vídeos, de preferência de uma playlist, para os assuntos que o
catálogo ainda não tem. O vídeo não é hospedado: o aluno assiste pelo player do
YouTube, e o que fica aqui é o que o identifica e a lacuna que ele cobre. A
transcrição (#208) parte dos vídeos em `aguardando`, e a segmentação (#209)
corta os transcritos em partes.
"""

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.academico import Lacuna
from app.models.base import Base, TimestampMixin
from app.models.enums import StatusVideo


class VideoYoutube(Base, TimestampMixin):
    __tablename__ = "videos_youtube"

    id: Mapped[int] = mapped_column(primary_key=True)
    # O `v=` da URL. Um vídeo que cobre lacunas de duas ementas é um só.
    youtube_id: Mapped[str] = mapped_column(String(20), unique=True)
    titulo: Mapped[str] = mapped_column(String(300))
    canal: Mapped[str | None] = mapped_column(String(200))
    duracao_segundos: Mapped[int | None]
    # A playlist de onde veio e a posição nela: a ordem das aulas, que o
    # professor do canal definiu e que a trilha (#210) aproveita.
    playlist_id: Mapped[str | None] = mapped_column(String(64))
    posicao: Mapped[int | None]
    status: Mapped[StatusVideo] = mapped_column(default=StatusVideo.aguardando, index=True)
    erro: Mapped[str | None] = mapped_column(Text)

    lacunas: Mapped[list["VideoLacuna"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    partes: Mapped[list["ParteVideo"]] = relationship(
        back_populates="video", cascade="all, delete-orphan", order_by="ParteVideo.ordem"
    )


class ParteVideo(Base, TimestampMixin):
    """Um pedaço do vídeo sobre um assunto só (#209): o que vira módulo da trilha (#210).

    O vídeo curto, o caso comum nas playlists, tem uma parte só, o vídeo
    inteiro. A parte não é um arquivo: é o intervalo que o player do YouTube
    toca (`?start=&end=`).
    """

    __tablename__ = "partes_video"
    __table_args__ = (UniqueConstraint("video_id", "ordem", name="uq_partes_video_video_ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos_youtube.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int]
    inicio_segundos: Mapped[float]
    fim_segundos: Mapped[float]
    titulo: Mapped[str] = mapped_column(String(200))
    resumo: Mapped[str | None] = mapped_column(Text)
    # A categorização (#202): a matéria da parte, a confiança da IA e a frase da
    # transcrição que justifica. `aprovada` é `None` antes de categorizar; a
    # parte aprovada vira módulo (#210), com as lacunas que cobre.
    disciplina: Mapped[str | None] = mapped_column(String(200))
    confianca: Mapped[float | None]
    justificativa: Mapped[str | None] = mapped_column(Text)
    aprovada: Mapped[bool | None]

    video: Mapped[VideoYoutube] = relationship(back_populates="partes")
    lacunas: Mapped[list[Lacuna]] = relationship(secondary="parte_lacunas")


class ParteLacuna(Base):
    """Que lacunas uma parte aprovada cobre, segundo a categorização."""

    __tablename__ = "parte_lacunas"

    parte_id: Mapped[int] = mapped_column(
        ForeignKey("partes_video.id", ondelete="CASCADE"), primary_key=True
    )
    lacuna_id: Mapped[int] = mapped_column(
        ForeignKey("lacunas.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class VideoLacuna(Base):
    """Qual vídeo cobre qual lacuna, e quão perto o título chegou do assunto."""

    __tablename__ = "video_lacunas"

    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos_youtube.id", ondelete="CASCADE"), primary_key=True
    )
    lacuna_id: Mapped[int] = mapped_column(
        ForeignKey("lacunas.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    # Distância de cosseno entre o assunto e o título do vídeo.
    distancia: Mapped[float]
    # A categorização (#202) viu que nenhuma parte do vídeo ensina o assunto: a
    # lacuna volta para a busca, que não escolhe este vídeo de novo para ela.
    recusada: Mapped[bool] = mapped_column(default=False, server_default=false())

    video: Mapped[VideoYoutube] = relationship(back_populates="lacunas")
    lacuna: Mapped[Lacuna] = relationship()


class BuscaYoutube(Base, TimestampMixin):
    """Resposta guardada de uma consulta à API: a mesma consulta não gasta cota de novo."""

    __tablename__ = "buscas_youtube"

    id: Mapped[int] = mapped_column(primary_key=True)
    # O recurso e os parâmetros da consulta, normalizados.
    chave: Mapped[str] = mapped_column(String(500), unique=True)
    resposta: Mapped[dict] = mapped_column(JSON)
