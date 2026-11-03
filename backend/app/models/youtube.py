"""Conteúdo do YouTube que cobre as lacunas das ementas (#207).

A busca escolhe vídeos, de preferência de uma playlist, para os assuntos que o
catálogo ainda não tem. O vídeo não é hospedado: o aluno assiste pelo player do
YouTube, e o que fica aqui é o que o identifica e a lacuna que ele cobre. A
transcrição (#208) parte dos vídeos em `aguardando`.
"""

from sqlalchemy import JSON, ForeignKey, String, Text
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

    video: Mapped[VideoYoutube] = relationship(back_populates="lacunas")
    lacuna: Mapped[Lacuna] = relationship()


class BuscaYoutube(Base, TimestampMixin):
    """Resposta guardada de uma consulta à API: a mesma consulta não gasta cota de novo."""

    __tablename__ = "buscas_youtube"

    id: Mapped[int] = mapped_column(primary_key=True)
    # O recurso e os parâmetros da consulta, normalizados.
    chave: Mapped[str] = mapped_column(String(500), unique=True)
    resposta: Mapped[dict] = mapped_column(JSON)
