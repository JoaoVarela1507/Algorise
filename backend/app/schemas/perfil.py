"""Contrato do perfil do aluno (tela 18) e do fim do onboarding (telas 7 a 15)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import NivelExperiencia, TipoTrilha

__all__ = ["AtualizacaoPerfil", "Perfil"]


class Perfil(BaseModel):
    """Tudo o que as telas privadas mostram do aluno.

    Mais completo que o `UsuarioAutenticado` do login: traz o que o onboarding
    coletou e o streak, que o `/auth/eu` não precisa carregar.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    nome_exibicao: str
    avatar_url: str | None = None
    xp_total: int = 0
    streak_dias: int = 0
    nivel_experiencia: NivelExperiencia
    tipo_trilha: TipoTrilha
    instituicao: str | None = None
    curso: str | None = None
    periodo: int | None = None


class AtualizacaoPerfil(BaseModel):
    """PATCH parcial: só os campos enviados mudam.

    Instituição e curso vêm por nome, como o aluno digitou no onboarding; o
    backend reaproveita o registro existente ou cria um novo.
    """

    nome_exibicao: str | None = Field(default=None, min_length=2, max_length=120)
    nivel_experiencia: NivelExperiencia | None = None
    tipo_trilha: TipoTrilha | None = None
    instituicao: str | None = Field(default=None, min_length=2, max_length=200)
    curso: str | None = Field(default=None, min_length=2, max_length=200)
    periodo: int | None = Field(default=None, ge=1, le=12)
