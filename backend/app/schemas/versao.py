from pydantic import BaseModel


class Versao(BaseModel):
    nome: str
    versao: str
    commit: str
    build: str | None = None
    ambiente: str
