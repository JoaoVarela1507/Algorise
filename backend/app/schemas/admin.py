"""Contrato da API administrativa: trilhas, passos, atividades e métricas (#41).

Diferente do contrato do aluno, aqui a atividade vem **com o gabarito**: é quem
escreve o conteúdo que precisa vê-lo.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import OrigemModulo, TipoAtividade

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Slug = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=120),
]


# --- atividades ---------------------------------------------------------------------------


class AtividadeEdicao(BaseModel):
    """Os campos que se pode mudar. O que não vem fica como está."""

    tipo: TipoAtividade | None = None
    enunciado: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    dica: str | None = None
    comando_esperado: Annotated[str, StringConstraints(max_length=500)] | None = None
    saida_esperada: str | None = None
    resposta_esperada: str | None = None
    tempo_sugerido_segundos: int | None = Field(default=None, ge=1, le=3600)
    xp: int | None = Field(default=None, ge=0, le=1000)


class AtividadeCriacao(AtividadeEdicao):
    passo_id: int
    tipo: TipoAtividade
    enunciado: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    # Sem ordem, entra no fim do passo.
    ordem: int | None = Field(default=None, ge=1)


class AtividadeAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    passo_id: int = Field(validation_alias="modulo_id")
    ordem: int
    tipo: TipoAtividade
    enunciado: str
    dica: str | None = None
    comando_esperado: str | None = None
    saida_esperada: str | None = None
    resposta_esperada: str | None = None
    tempo_sugerido_segundos: int | None = None
    xp: int


# --- passos -------------------------------------------------------------------------------


class PassoEdicao(BaseModel):
    titulo: Nome | None = None
    descricao: str | None = None
    video_url: Annotated[str, StringConstraints(max_length=500)] | None = None
    inicio_segundos: float | None = Field(default=None, ge=0)
    fim_segundos: float | None = Field(default=None, gt=0)
    # Mover o passo: os outros se ajustam, e o progresso dos alunos continua no passo.
    ordem: int | None = Field(default=None, ge=1)


class PassoCriacao(PassoEdicao):
    titulo: Nome


class PassoAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ordem: int
    titulo: str
    descricao: str | None = None
    video_url: str | None = None
    inicio_segundos: float | None = None
    fim_segundos: float | None = None
    origem: OrigemModulo
    atividades: list[AtividadeAdmin] = []


# --- trilhas ------------------------------------------------------------------------------


class TrilhaEdicao(BaseModel):
    nome: Nome | None = None
    disciplina: Nome | None = None
    categoria: Annotated[str, StringConstraints(max_length=80)] | None = None
    periodo: int | None = Field(default=None, ge=1, le=12)
    descricao: str | None = None


class TrilhaCriacao(TrilhaEdicao):
    slug: Slug
    nome: Nome
    disciplina: Nome


class TrilhaAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    nome: str
    disciplina: str
    categoria: str | None = None
    periodo: int | None = None
    descricao: str | None = None
    publicada: bool
    passos: list[PassoAdmin] = Field(default=[], validation_alias="modulos")


class Publicacao(BaseModel):
    publicada: bool


class ProblemaDeConteudo(BaseModel):
    """O que impede publicar: onde está e o que falta."""

    passo: int | None = None
    atividade: int | None = None
    problema: str


# --- importação ---------------------------------------------------------------------------


class AtividadeImportada(AtividadeEdicao):
    tipo: TipoAtividade
    enunciado: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PassoImportado(PassoEdicao):
    titulo: Nome
    atividades: list[AtividadeImportada] = []


class TrilhaImportada(TrilhaCriacao):
    """Uma trilha inteira. Importar de novo o mesmo slug atualiza, em vez de duplicar."""

    publicada: bool = False
    passos: list[PassoImportado] = Field(min_length=1)


# --- métricas -----------------------------------------------------------------------------


class ErroComum(BaseModel):
    resposta: str
    vezes: int


class MetricasAtividade(BaseModel):
    atividade_id: int
    passo: int
    ordem: int
    tipo: TipoAtividade
    tentativas: int
    alunos: int
    acertos: int
    taxa_de_acerto: float
    # Alunos que tentaram e nunca acertaram, sobre os que tentaram.
    abandono: float
    # Só nas de terminal: as respostas erradas que mais se repetem.
    erros_comuns: list[ErroComum] = []


class MetricasTrilha(BaseModel):
    trilha_id: int
    slug: str
    nome: str
    publicada: bool
    alunos_iniciaram: int
    alunos_concluiram: int
    taxa_de_conclusao: float
    atividades: list[MetricasAtividade]
