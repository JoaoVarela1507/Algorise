from pydantic import BaseModel, ConfigDict

from app.models.enums import TipoAtividade


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    ordem: int
    titulo: str
    descricao: str | None = None
    video_url: str | None = None
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
    progresso: int = 0


class TrilhaDetalhe(Trilha):
    descricao: str | None = None
    modulos: list[ModuloDetalhe] = []
