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
from app.models.chat import Conversa, GrupoChat, MensagemChat
from app.models.enums import (
    ModoResposta,
    NivelExperiencia,
    OrigemModulo,
    OrigemVault,
    OrigemXP,
    PapelMensagem,
    PapelUsuario,
    StatusAssuntos,
    StatusEmenta,
    StatusGeracao,
    StatusLacuna,
    StatusProgresso,
    StatusVideo,
    TamanhoFonte,
    TipoAtividade,
    TipoTrilha,
)
from app.models.gamificacao import Certificado, Parceiro, Streak, XPEvento
from app.models.progresso import ProgressoUsuario, RespostaUsuario
from app.models.trilha import Atividade, ExerciciosGerados, Modulo, ReporteModulo, Trilha
from app.models.usuario import Consentimento, ContaOAuth, Usuario
from app.models.vault import DocumentoVault, TrechoVault
from app.models.youtube import (
    BuscaYoutube,
    ParteLacuna,
    ParteVideo,
    VideoLacuna,
    VideoYoutube,
)

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
    "ExerciciosGerados",
    "GrupoChat",
    "Instituicao",
    "Lacuna",
    "MensagemChat",
    "ModoResposta",
    "Modulo",
    "NivelExperiencia",
    "OrigemModulo",
    "OrigemVault",
    "OrigemXP",
    "PapelMensagem",
    "PapelUsuario",
    "Parceiro",
    "ParteLacuna",
    "ParteVideo",
    "ProgressoUsuario",
    "ReporteModulo",
    "RespostaUsuario",
    "StatusAssuntos",
    "StatusEmenta",
    "StatusGeracao",
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
