from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusProgresso, TipoAtividade


class AtividadeResumo(BaseModel):
    """Atividade sem gabarito — é o que pode ir para o cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ordem: int
    tipo: TipoAtividade
    enunciado: str
    dica: str | None = None
    tempo_sugerido_segundos: int | None = None
    xp: int


class Modulo(BaseModel):
    """Um passo do caminho da tela 26."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ordem: int
    titulo: str
    descricao: str | None = None
    video_url: str | None = None
    # Quem decide é o servidor (ver `app/services/progresso.py`). `concluido` e
    # `bloqueado` continuam porque a tela já os usa; `status` é a forma completa,
    # que distingue o passo atual dos que ainda nem abriram.
    status: StatusProgresso = StatusProgresso.bloqueado
    concluido: bool = False
    bloqueado: bool = True


class ModuloDetalhe(Modulo):
    atividades: list[AtividadeResumo] = []


class Trilha(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    nome: str
    disciplina: str
    categoria: str | None = None
    periodo: int | None = None
    total_modulos: int = 0
    # Quantos passos o aluno fechou: é o "3" do "3/10" da tela 24. Zero para
    # quem não está autenticado.
    progresso: int = 0


class TrilhaDetalhe(Trilha):
    descricao: str | None = None
    modulos: list[ModuloDetalhe] = []


class TrilhaRecomendada(Trilha):
    """Card da seção de sugestões da tela 24."""

    # Por que ela apareceu: o texto vai no próprio card.
    motivo: str


class PassoDetalhe(ModuloDetalhe):
    """Conteúdo de um passo, com o bastante para a tela 26 se situar."""

    trilha_slug: str
    trilha_nome: str
    total_passos: int
    # Ordem do próximo passo, ou None quando este é o último.
    proximo: int | None = None
