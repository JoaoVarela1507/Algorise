from enum import Enum

from pydantic import BaseModel, EmailStr


class NivelExperiencia(str, Enum):
    baixo = "baixo"
    medio = "medio"
    alto = "alto"


class TipoTrilha(str, Enum):
    guiada = "guiada"
    livre = "livre"
    mista = "mista"


class Usuario(BaseModel):
    id: str
    nome: str
    email: EmailStr
    nivel_experiencia: NivelExperiencia
    tipo_trilha: TipoTrilha
    xp: int = 0
    streak_dias: int = 0
    instituicao: str | None = None
    curso: str | None = None
