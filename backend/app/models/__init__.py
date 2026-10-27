"""Modelos do Algorise.

Todos são importados aqui para que `Base.metadata` fique completo — é disso que
o Alembic depende para detectar as tabelas.
"""

from app.models.academico import Curso, Ementa, Instituicao
from app.models.base import Base, TimestampMixin
from app.models.chat import Conversa, MensagemChat
from app.models.enums import (
    ModoResposta,
    NivelExperiencia,
    OrigemVault,
    OrigemXP,
    PapelMensagem,
    StatusEmenta,
    StatusProgresso,
    TamanhoFonte,
    TipoAtividade,
    TipoTrilha,
)
from app.models.gamificacao import Certificado, Streak, XPEvento
from app.models.progresso import ProgressoUsuario, RespostaUsuario
from app.models.trilha import Atividade, Modulo, Trilha
from app.models.usuario import Consentimento, ContaOAuth, Usuario
from app.models.vault import DocumentoVault, TrechoVault

__all__ = [
    "Atividade",
    "Base",
    "Certificado",
    "Consentimento",
    "ContaOAuth",
    "Conversa",
    "Curso",
    "DocumentoVault",
    "Ementa",
    "Instituicao",
    "MensagemChat",
    "ModoResposta",
    "Modulo",
    "NivelExperiencia",
    "OrigemVault",
    "OrigemXP",
    "PapelMensagem",
    "ProgressoUsuario",
    "RespostaUsuario",
    "StatusEmenta",
    "StatusProgresso",
    "Streak",
    "TamanhoFonte",
    "TimestampMixin",
    "TipoAtividade",
    "TipoTrilha",
    "TrechoVault",
    "Trilha",
    "Usuario",
    "XPEvento",
]
