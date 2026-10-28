"""Contrato da trilha guiada do aluno, montada da ementa confirmada (#38)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import NivelExperiencia, StatusLacuna, StatusProgresso


class ModuloGuiado(BaseModel):
    id: int
    titulo: str
    # Com a trilha e a ordem, o frontend abre o passo em `/trilhas/{slug}`.
    ordem: int
    trilha_slug: str
    trilha_nome: str
    status: StatusProgresso


class ItemGuiado(BaseModel):
    # `modulo`: um passo de uma trilha do catálogo. `lacuna`: o assunto ainda
    # não tem conteúdo, e a busca (#207) está em `status_lacuna`.
    tipo: Literal["modulo", "lacuna"]
    disciplina: str
    periodo: int | None = None
    # Os assuntos da ementa que o item cobre. Vazio num módulo `base`.
    assuntos: list[str]
    # Entrou pelo nível baixo, como pré-requisito dos assuntos.
    base: bool = False
    modulo: ModuloGuiado | None = None
    status_lacuna: StatusLacuna | None = None


class TrilhaGuiada(BaseModel):
    ementa_id: int
    confirmada_em: datetime
    nivel: NivelExperiencia
    itens: list[ItemGuiado]
    total_modulos: int
    concluidos: int
