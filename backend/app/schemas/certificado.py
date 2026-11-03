"""Contrato dos certificados (tela 20) e da validação pública (#32)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Certificado(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trilha_id: int
    codigo: str
    parceiro: str | None = None
    emitido_em: datetime | None = None
    nome_aluno: str | None = None
    nome_trilha: str | None = None
    disciplina: str | None = None
    carga_horaria: int | None = None


class ItemDeCertificado(BaseModel):
    """Uma trilha de parceiro: o certificado liberado ou o que falta para ele."""

    trilha_id: int
    slug: str
    nome: str
    disciplina: str
    parceiro: str
    carga_horaria: int | None = None
    total_modulos: int
    concluidos: int
    estado: Literal["liberado", "bloqueado"]
    # Só no liberado.
    certificado_id: int | None = None


class PeriodoDeCertificados(BaseModel):
    # `None`: trilha sem período (optativa).
    periodo: int | None = None
    itens: list[ItemDeCertificado]


class Validacao(BaseModel):
    """O que o certificado diz, para quem confere o código. Nada mais do aluno."""

    codigo: str
    nome_aluno: str | None = None
    nome_trilha: str | None = None
    disciplina: str | None = None
    carga_horaria: int | None = None
    parceiro: str | None = None
    emitido_em: datetime | None = None
