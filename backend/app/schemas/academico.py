"""Contrato do catálogo acadêmico e da ementa do onboarding (telas 14 e 15)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusAssuntos, StatusEmenta, StatusLacuna

__all__ = [
    "AssuntoLido",
    "AssuntosDaEmenta",
    "CursoResumo",
    "DisciplinaLida",
    "EmentaStatus",
    "InstituicaoResumo",
    "ModuloDoAssunto",
    "PeriodoCurso",
]


class InstituicaoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    sigla: str | None = None
    uf: str | None = None


class CursoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    total_periodos: int


class PeriodoCurso(BaseModel):
    numero: int
    # As disciplinas que o catálogo do Algorise cobre neste período.
    disciplinas: list[str]


class EmentaStatus(BaseModel):
    """Onde está o processamento. O texto extraído não sai daqui: é insumo da #38."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatusEmenta
    nome_original: str | None = None
    tamanho_bytes: int | None = None
    paginas: int | None = None
    # Motivo da falha, escrito para o aluno.
    erro: str | None = None
    # A leitura das disciplinas e dos assuntos pela IA (#38), depois do texto.
    status_assuntos: StatusAssuntos
    erro_assuntos: str | None = None
    criado_em: datetime


class ModuloDoAssunto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    trilha_id: int


class AssuntoLido(BaseModel):
    texto: str
    # `coberto`: há um módulo no catálogo para o assunto. `lacuna`: ainda não,
    # e `status_lacuna` diz em que pé está a busca de conteúdo.
    situacao: Literal["coberto", "lacuna"]
    modulo: ModuloDoAssunto | None = None
    status_lacuna: StatusLacuna | None = None


class DisciplinaLida(BaseModel):
    nome: str
    periodo: int | None = None
    carga_horaria: int | None = None
    assuntos: list[AssuntoLido]


class AssuntosDaEmenta(BaseModel):
    """O que a IA leu da ementa e onde cada assunto está no catálogo (#38)."""

    status_assuntos: StatusAssuntos
    erro_assuntos: str | None = None
    # Vazia até `status_assuntos` chegar a `prontos`.
    disciplinas: list[DisciplinaLida]
