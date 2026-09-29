from pydantic import BaseModel, EmailStr

# Os enums vivem no domínio, não no schema: banco e API compartilham a mesma
# definição.
from app.models import Usuario as UsuarioModelo
from app.models.enums import NivelExperiencia, TipoTrilha

__all__ = ["NivelExperiencia", "TipoTrilha", "Usuario"]


class Usuario(BaseModel):
    id: str
    username: str
    nome: str
    email: EmailStr
    avatar_url: str | None = None
    nivel_experiencia: NivelExperiencia
    tipo_trilha: TipoTrilha
    xp: int = 0
    streak_dias: int = 0
    instituicao: str | None = None
    curso: str | None = None
    periodo: int | None = None

    @classmethod
    def do_modelo(cls, usuario: UsuarioModelo) -> "Usuario":
        # Os nomes da API não batem com as colunas (`nome` x `nome_exibicao`,
        # `xp` x `xp_total`), então a conversão é explícita em vez de
        # `from_attributes`.
        return cls(
            id=str(usuario.id),
            username=usuario.username,
            nome=usuario.nome_exibicao,
            email=usuario.email,
            avatar_url=usuario.avatar_url,
            nivel_experiencia=usuario.nivel_experiencia,
            tipo_trilha=usuario.tipo_trilha,
            xp=usuario.xp_total,
            streak_dias=usuario.streak.dias_consecutivos if usuario.streak else 0,
            instituicao=usuario.instituicao.nome if usuario.instituicao else None,
            curso=usuario.curso.nome if usuario.curso else None,
            periodo=usuario.periodo,
        )
