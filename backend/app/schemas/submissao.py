"""Contrato das submissões de atividade (telas 28 a 38)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Correcao", "PassoConcluido", "Submissao", "Tentativa"]

# Teto do que o aluno manda. Comando de terminal tem dezenas de caracteres;
# resposta aberta, alguns parágrafos. O limite existe para uma submissão não
# virar um jeito barato de encher o banco.
TAMANHO_MAXIMO_RESPOSTA = 5_000


class Submissao(BaseModel):
    """O que o aluno envia."""

    conteudo: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_RESPOSTA)
    # Quanto tempo levou, para as métricas de aprendizado. Opcional: o cliente
    # pode não ter medido.
    tempo_gasto_segundos: int | None = Field(default=None, ge=0, le=60 * 60 * 6)


class Tentativa(BaseModel):
    """Uma tentativa já registrada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tentativa: int
    conteudo: str
    correta: bool
    feedback: str | None = None
    tempo_gasto_segundos: int | None = None
    criado_em: datetime


class Correcao(BaseModel):
    """A resposta da submissão."""

    correta: bool
    # A resposta ficou guardada esperando a correção por IA (#11).
    em_analise: bool
    feedback: str
    tentativa: int
    # XP ganho **nesta** submissão: zero quando o aluno já tinha acertado antes.
    xp_ganho: int
    xp_total: int


class PassoConcluido(BaseModel):
    """O que volta ao fechar um passo."""

    xp_ganho: int
    xp_total: int
    # Ordem do próximo passo, ou None quando este era o último da trilha.
    proximo: int | None = None
