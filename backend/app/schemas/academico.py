"""Contrato do catálogo acadêmico e da ementa do onboarding (telas 14 e 15)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import StatusAssuntos, StatusEmenta, StatusLacuna

__all__ = [
    "AssuntoLido",
    "AssuntosDaEmenta",
    "AssuntosRevisados",
    "CursoResumo",
    "DisciplinaLida",
    "DisciplinaRevisada",
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
    # O trecho lido (1 a `paginas`): no PPC, só o ementário.
    pagina_inicial: int | None = None
    pagina_final: int | None = None
    # Motivo da falha, escrito para o aluno.
    erro: str | None = None
    # A leitura das disciplinas e dos assuntos pela IA (#38), depois do texto.
    status_assuntos: StatusAssuntos
    erro_assuntos: str | None = None
    # Quando o aluno revisou os assuntos e pediu a trilha guiada.
    confirmada_em: datetime | None = None
    criado_em: datetime


class ModuloDoAssunto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    trilha_id: int


class AssuntoLido(BaseModel):
    texto: str
    # `coberto`: há um módulo no catálogo para o assunto. `lacuna`: ainda não,
    # e `status_lacuna` diz em que pé está a busca de conteúdo. `fora`: a
    # disciplina não entra na trilha guiada, e o assunto não foi ao catálogo.
    situacao: Literal["coberto", "lacuna", "fora"]
    modulo: ModuloDoAssunto | None = None
    status_lacuna: StatusLacuna | None = None


class DisciplinaLida(BaseModel):
    nome: str
    periodo: int | None = None
    carga_horaria: int | None = None
    # Entra na trilha guiada: de programação, segundo a IA ou o aluno.
    na_trilha: bool
    assuntos: list[AssuntoLido]


class AssuntosDaEmenta(BaseModel):
    """O que a IA leu da ementa e onde cada assunto está no catálogo (#38)."""

    status_assuntos: StatusAssuntos
    erro_assuntos: str | None = None
    # Vazia até `status_assuntos` chegar a `prontos`.
    disciplinas: list[DisciplinaLida]


Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class DisciplinaRevisada(BaseModel):
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    periodo: int | None = Field(default=None, ge=1, le=20)
    carga_horaria: int | None = Field(default=None, ge=1, le=2000)
    na_trilha: bool = True
    assuntos: list[Texto] = Field(min_length=1, max_length=200)


class AssuntosRevisados(BaseModel):
    """A lista inteira, como o aluno deixou na revisão: o que sai dela é removido."""

    disciplinas: list[DisciplinaRevisada] = Field(min_length=1, max_length=50)
