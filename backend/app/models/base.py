from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database import metadata


class Base(DeclarativeBase):
    """Base de todos os modelos, com a convenção de nomes de constraints."""

    metadata = metadata


class TimestampMixin:
    """Carimbo de criação e atualização, preenchido pelo próprio banco."""

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
