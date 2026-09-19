from enum import Enum

from pydantic import BaseModel


class TipoQuestao(str, Enum):
    multipla_escolha = "multipla-escolha"
    ordenacao = "ordenacao"
    preencher_lacuna = "preencher-lacuna"


class Questao(BaseModel):
    id: str
    tipo: TipoQuestao
    enunciado: str
    codigo: str | None = None
    opcoes: list[str] | None = None
    resposta_correta: str | list[str]
