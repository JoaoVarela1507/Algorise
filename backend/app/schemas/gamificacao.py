"""Contrato da gamificação (telas 16 e 20)."""

from pydantic import BaseModel, Field

__all__ = ["Painel"]


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
