"""Contrato do desafio de código (#34, telas 40 a 42)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.models.enums import StatusExecucao


class CasoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ordem: int
    entrada: str
    saida_esperada: str


class Desafio(BaseModel):
    id: int
    enunciado: str
    dica: str | None = None
    xp: int
    casos_publicos: list[CasoPublico]
    # Os ocultos contam na correção, mas só o número aparece.
    total_casos: int
    linguagem: str = "python"


class NovaExecucao(BaseModel):
    codigo: str = Field(min_length=1, max_length=settings.sandbox_codigo_maximo)


class ExecucaoNaFila(BaseModel):
    id: str
    status: StatusExecucao


class ResultadoDoCaso(BaseModel):
    ordem: int
    publico: bool
    passou: bool
    # `tempo_esgotado`, `memoria_estourada`, `saida_grande_demais`,
    # `erro_de_execucao` ou `saida_diferente`.
    motivo: str | None = None
    # Só nos casos públicos.
    entrada: str | None = None
    esperado: str | None = None
    obtido: str | None = None


class ExecucaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    atividade_id: int
    status: StatusExecucao
    aprovada: bool
    stdout: str
    stderr: str
    casos: list[ResultadoDoCaso]
    erro: str | None = None
    criado_em: datetime
    terminada_em: datetime | None = None
