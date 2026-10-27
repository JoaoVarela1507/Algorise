"""Contrato do perfil do aluno (telas 18 e 19) e do fim do onboarding (telas 7 a 15)."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import NivelExperiencia, TamanhoFonte, TipoTrilha

__all__ = [
    "AtualizacaoPerfil",
    "AtualizacaoPreferencias",
    "Onboarding",
    "Perfil",
    "PerfilPublico",
    "Preferencias",
    "TrocaDeTrilha",
]


class Preferencias(BaseModel):
    """Acessibilidade escolhida pelo aluno, que vale em qualquer aparelho."""

    model_config = ConfigDict(from_attributes=True)

    tamanho_fonte: TamanhoFonte = TamanhoFonte.normal
    alto_contraste: bool = False
    reduzir_animacoes: bool = False


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
    # Conta entra por senha (e não só por GitHub/Google): decide se a exclusão
    # da conta e a troca de senha pedem a senha atual.
    tem_senha: bool = False
    xp_total: int = 0
    # Mesma conta do `/gamificacao/me`: o cliente não precisa conhecer a curva.
    nivel: int = 1
    xp_no_nivel: int = 0
    xp_para_proximo: int = 0
    streak_dias: int = 0
    nivel_experiencia: NivelExperiencia
    tipo_trilha: TipoTrilha
    instituicao: str | None = None
    curso: str | None = None
    periodo: int | None = None
    preferencias: Preferencias = Field(default_factory=Preferencias)
    # Nulo é quem ainda não passou pelo onboarding (telas 7 a 15).
    onboarding_concluido_em: datetime | None = None


class PerfilPublico(BaseModel):
    """O que um aluno vê de outro (ranking): nada além do que o ranking já mostra.

    Sem e-mail, instituição, curso ou período: são dados pessoais que o aluno
    informou para o próprio plano de estudos, não para exibir.
    """

    username: str
    nome_exibicao: str
    avatar_url: str | None = None
    nivel: int
    xp_total: int
    streak_dias: int


class AtualizacaoPerfil(BaseModel):
    """PATCH parcial: só os campos enviados mudam.

    Instituição e curso vêm por nome, como o aluno digitou no onboarding; o
    backend reaproveita o registro existente ou cria um novo.
    """

    nome_exibicao: str | None = Field(default=None, min_length=2, max_length=120)
    nivel_experiencia: NivelExperiencia | None = None
    # Continua aqui porque o onboarding grava tudo numa chamada só; a troca pelo
    # perfil usa `PATCH /usuarios/me/trilha`. As duas passam pela mesma regra.
    tipo_trilha: TipoTrilha | None = None
    instituicao: str | None = Field(default=None, min_length=2, max_length=200)
    curso: str | None = Field(default=None, min_length=2, max_length=200)
    periodo: int | None = Field(default=None, ge=1, le=12)


class AtualizacaoPreferencias(BaseModel):
    """PATCH parcial das preferências: o que não vier fica como está."""

    tamanho_fonte: TamanhoFonte | None = None
    alto_contraste: bool | None = None
    reduzir_animacoes: bool | None = None


class Onboarding(BaseModel):
    """O fim do onboarding, numa chamada só (telas 7 a 15).

    Instituição e curso vêm de um de dois jeitos: pelo `id`, quando o aluno
    escolheu uma sugestão do autocomplete, ou pelo nome, quando digitou algo
    que não está no catálogo. O texto livre não trava o fluxo: vira um registro
    do aluno, que só não aparece como sugestão para os outros.

    É o retrato completo do onboarding: o que não vier fica vazio no perfil.
    """

    nivel_experiencia: NivelExperiencia
    tipo_trilha: TipoTrilha
    instituicao_id: int | None = None
    instituicao: str | None = Field(default=None, min_length=2, max_length=200)
    curso_id: int | None = None
    curso: str | None = Field(default=None, min_length=2, max_length=200)
    periodo: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def _um_jeito_so(self) -> Self:
        if self.instituicao_id is not None and self.instituicao is not None:
            raise ValueError("Informe a instituição pelo id ou pelo nome, não pelos dois")
        if self.curso_id is not None and self.curso is not None:
            raise ValueError("Informe o curso pelo id ou pelo nome, não pelos dois")
        # Curso pelo id já diz a instituição; pelo nome, não.
        if self.curso is not None and self.instituicao_id is None and self.instituicao is None:
            raise ValueError("Informe a instituição antes do curso")
        return self


class TrocaDeTrilha(BaseModel):
    tipo_trilha: TipoTrilha
