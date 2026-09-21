from pydantic import BaseModel

from app.models.enums import TipoAtividade

__all__ = ["Questao", "TipoAtividade"]


class Questao(BaseModel):
    id: str
    tipo: TipoAtividade
    enunciado: str
    codigo: str | None = None
    opcoes: list[str] | None = None
    resposta_correta: str | list[str]
