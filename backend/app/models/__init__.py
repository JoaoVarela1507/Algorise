"""Modelos do Algorise.

Todos são importados aqui para que `Base.metadata` fique completo — é disso que
o Alembic depende para detectar as tabelas.
"""

from app.models.academico import (
    AssuntoEmenta,
    Curso,
    DisciplinaEmenta,
    Ementa,
    Instituicao,
    Lacuna,
)
from app.models.base import Base, TimestampMixin
from app.models.chat import Conversa, MensagemChat
from app.models.enums import (
    ModoResposta,
    NivelExperiencia,
    OrigemVault,
    OrigemXP,
    PapelMensagem,
    StatusAssuntos,
    StatusEmenta,
    StatusLacuna,
    StatusProgresso,
    StatusVideo,
    TamanhoFonte,
    TipoAtividade,
    TipoTrilha,
)
from app.models.gamificacao import Certificado, Streak, XPEvento
from app.models.progresso import ProgressoUsuario, RespostaUsuario
from app.models.trilha import Atividade, Modulo, Trilha
from app.models.usuario import Consentimento, ContaOAuth, Usuario
from app.models.vault import DocumentoVault, TrechoVault
from app.models.youtube import BuscaYoutube, VideoLacuna, VideoYoutube

__all__ = [
    "AssuntoEmenta",
    "Atividade",
    "Base",
    "BuscaYoutube",
    "Certificado",
    "Consentimento",
    "ContaOAuth",
    "Conversa",
    "Curso",
    "DisciplinaEmenta",
    "DocumentoVault",
    "Ementa",
    "Instituicao",
    "Lacuna",
    "MensagemChat",
    "ModoResposta",
    "Modulo",
    "NivelExperiencia",
    "OrigemVault",
    "OrigemXP",
    "PapelMensagem",
    "ProgressoUsuario",
    "RespostaUsuario",
    "StatusAssuntos",
    "StatusEmenta",
    "StatusLacuna",
    "StatusProgresso",
    "StatusVideo",
    "Streak",
    "TamanhoFonte",
    "TimestampMixin",
    "TipoAtividade",
    "TipoTrilha",
    "TrechoVault",
    "Trilha",
    "Usuario",
    "VideoLacuna",
    "VideoYoutube",
    "XPEvento",
]
