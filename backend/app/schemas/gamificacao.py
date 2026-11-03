"""Contrato da gamificação (telas 16 e 20)."""

from pydantic import BaseModel, Field

__all__ = ["Conquista", "MetaDiaria", "Painel"]


class Painel(BaseModel):
    """XP, nível e streak do aluno, como as telas mostram."""

    xp_total: int = Field(ge=0)
    nivel: int = Field(ge=1)
    # Onde o aluno está dentro do nível e quanto falta: é o que a barra de
    # progresso desenha, sem o cliente precisar conhecer a curva.
    xp_no_nivel: int = Field(ge=0)
    xp_para_o_proximo: int = Field(ge=0)
    streak_dias: int = Field(ge=0)
    maior_streak: int = Field(ge=0)


class MetaDiaria(BaseModel):
    """O anel de meta do dia da home (tela 16), no fuso do aluno."""

    xp_hoje: int = Field(ge=0)
    xp_meta: int = Field(ge=1)
    desafios_resolvidos: int = Field(ge=0)
    minutos_estudados: int = Field(ge=0)


class Conquista(BaseModel):
    """Uma medalha do card de conquistas (tela 16).

    O `id` é estável: o frontend escolhe o ícone por ele.
    """

    id: str
    titulo: str
    descricao: str
    desbloqueada: bool
