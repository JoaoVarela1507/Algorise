from pydantic import BaseModel, EmailStr

# Os enums vivem no domínio, não no schema: banco e API compartilham a mesma
# definição.
from app.models.enums import NivelExperiencia, TipoTrilha

__all__ = ["NivelExperiencia", "TipoTrilha", "Usuario"]


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
