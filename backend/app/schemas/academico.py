"""Contrato do catálogo acadêmico e da ementa do onboarding (telas 14 e 15)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusEmenta

__all__ = ["CursoResumo", "EmentaStatus", "InstituicaoResumo", "PeriodoCurso"]


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
    criado_em: datetime
