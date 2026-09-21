from datetime import datetime
from enum import Enum as EnumPython

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database import metadata
from app.models.enums import (
    NivelExperiencia,
    OrigemXP,
    StatusEmenta,
    StatusProgresso,
    TipoAtividade,
    TipoTrilha,
)


def _enum(tipo: type[EnumPython]) -> Enum:
    """Tipo ENUM do PostgreSQL gravando o *valor* do membro, não o nome.

    Por padrão o SQLAlchemy grava o nome (`resposta_aberta`), enquanto a API
    troca o valor (`resposta-aberta`). A diferença só aparece em consulta
    manual, seed ou dump — e aí custa caro. `values_callable` alinha os dois.
    """
    return Enum(tipo, values_callable=lambda e: [membro.value for membro in e])


class Base(DeclarativeBase):
    """Base de todos os modelos, com a convenção de nomes de constraints."""

    metadata = metadata

    # Mapeia cada enum de domínio uma vez só; os modelos apenas anotam o tipo.
    type_annotation_map = {
        NivelExperiencia: _enum(NivelExperiencia),
        TipoTrilha: _enum(TipoTrilha),
        TipoAtividade: _enum(TipoAtividade),
        StatusProgresso: _enum(StatusProgresso),
        StatusEmenta: _enum(StatusEmenta),
        OrigemXP: _enum(OrigemXP),
    }


class TimestampMixin:
    """Carimbo de criação e atualização, preenchido pelo próprio banco."""

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
