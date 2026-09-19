from pydantic import BaseModel


class Modulo(BaseModel):
    id: str
    titulo: str
    ordem: int
    concluido: bool = False
    bloqueado: bool = True


class Trilha(BaseModel):
    id: str
    nome: str
    disciplina: str
    progresso: int = 0
    total_modulos: int
    modulos: list[Modulo] = []
