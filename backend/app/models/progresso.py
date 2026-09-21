"""Avanço do aluno na trilha e suas tentativas nas atividades."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import StatusProgresso


class ProgressoUsuario(Base, TimestampMixin):
    __tablename__ = "progresso_usuario"
    __table_args__ = (
        UniqueConstraint("usuario_id", "modulo_id", name="uq_progresso_usuario_modulo"),
        Index("ix_progresso_usuario_trilha", "usuario_id", "trilha_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    trilha_id: Mapped[int] = mapped_column(ForeignKey("trilhas.id", ondelete="CASCADE"))
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"))
    status: Mapped[StatusProgresso] = mapped_column(default=StatusProgresso.bloqueado)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RespostaUsuario(Base, TimestampMixin):
    """Cada tentativa, não só a última: é a base das métricas de aprendizado."""

    __tablename__ = "respostas_usuario"
    __table_args__ = (Index("ix_respostas_usuario_atividade", "usuario_id", "atividade_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividades.id", ondelete="CASCADE"))
    tentativa: Mapped[int] = mapped_column(default=1)
    conteudo: Mapped[str] = mapped_column(Text)
    correta: Mapped[bool] = mapped_column(default=False)
    tempo_gasto_segundos: Mapped[int | None]
    feedback: Mapped[str | None] = mapped_column(Text)
