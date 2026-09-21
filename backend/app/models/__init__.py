"""Modelos do Algorise.

Todos são importados aqui para que `Base.metadata` fique completo — é disso que
o Alembic depende para detectar as tabelas.
"""

from app.models.academico import Curso, Ementa, Instituicao
from app.models.base import Base, TimestampMixin
from app.models.enums import (
    NivelExperiencia,
    OrigemXP,
    StatusEmenta,
    StatusProgresso,
    TipoAtividade,
    TipoTrilha,
)
from app.models.gamificacao import Certificado, Streak, XPEvento
from app.models.progresso import ProgressoUsuario, RespostaUsuario
from app.models.trilha import Atividade, Modulo, Trilha
from app.models.usuario import Usuario

__all__ = [
    "Atividade",
    "Base",
    "Certificado",
    "Curso",
    "Ementa",
    "Instituicao",
    "Modulo",
    "NivelExperiencia",
    "OrigemXP",
    "ProgressoUsuario",
    "RespostaUsuario",
    "StatusEmenta",
    "StatusProgresso",
    "Streak",
    "TimestampMixin",
    "TipoAtividade",
    "TipoTrilha",
    "Trilha",
    "Usuario",
    "XPEvento",
]
