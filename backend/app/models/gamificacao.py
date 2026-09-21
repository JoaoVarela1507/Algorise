"""XP, streak e certificados — o que aparece nas telas 16, 20 e 38."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import OrigemXP


class XPEvento(Base, TimestampMixin):
    """Fonte da verdade do XP. `usuarios.xp_total` é só um cache disso."""

    __tablename__ = "xp_eventos"
    __table_args__ = (Index("ix_xp_eventos_usuario_data", "usuario_id", "criado_em"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    origem: Mapped[OrigemXP]
    # Id do que gerou o XP (atividade, módulo, trilha...). Sem FK porque a
    # origem varia.
    referencia_id: Mapped[int | None]
    valor: Mapped[int]


class Streak(Base, TimestampMixin):
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    dias_consecutivos: Mapped[int] = mapped_column(default=0)
    maior_sequencia: Mapped[int] = mapped_column(default=0)
    ultimo_acesso: Mapped[date | None] = mapped_column(Date)

    usuario: Mapped["Usuario"] = relationship(back_populates="streak")  # noqa: F821


class Certificado(Base, TimestampMixin):
    __tablename__ = "certificados"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    trilha_id: Mapped[int] = mapped_column(ForeignKey("trilhas.id", ondelete="CASCADE"))
    # Usado na validação pública (#32).
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    parceiro: Mapped[str | None] = mapped_column(String(120))
    emitido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
