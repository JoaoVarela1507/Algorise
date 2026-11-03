from pydantic import BaseModel, ConfigDict

from app.models.enums import OrigemModulo, StatusGeracao, StatusProgresso, TipoAtividade


class AtividadeResumo(BaseModel):
    """Atividade sem gabarito — é o que pode ir para o cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ordem: int
    tipo: TipoAtividade
    enunciado: str
    dica: str | None = None
    # Alternativas, itens a ordenar ou banco de palavras, conforme o tipo.
    opcoes: list[str] | None = None
    # Trecho de código da atividade; na lacuna, cada `___` é um buraco.
    codigo: str | None = None
    tempo_sugerido_segundos: int | None = None
    xp: int
    # Se o aluno já acertou: é o "2/4 atividades" do detalhe do módulo (tela 26).
    # Sempre falso para visitante.
    concluida: bool = False


class Modulo(BaseModel):
    """Um passo do caminho da tela 26."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ordem: int
    titulo: str
    descricao: str | None = None
    video_url: str | None = None
    # O trecho do vídeo que o player toca; sem eles, o vídeo inteiro (#210).
    inicio_segundos: float | None = None
    fim_segundos: float | None = None
    # `youtube`: feito de um vídeo pela busca de conteúdo, com o canal de
    # origem, e pode ser reportado.
    origem: OrigemModulo = OrigemModulo.manual
    canal: str | None = None
    # Quem decide é o servidor (ver `app/services/progresso.py`). `concluido` e
    # `bloqueado` continuam porque a tela já os usa; `status` é a forma completa,
    # que distingue o passo atual dos que ainda nem abriram.
    status: StatusProgresso = StatusProgresso.bloqueado
    concluido: bool = False
    bloqueado: bool = True


class ModuloDetalhe(Modulo):
    atividades: list[AtividadeResumo] = []
    # O que o passo paga ao todo: as atividades mais o bônus de fechá-lo.
    xp: int = 0


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
    # Só trilha de parceiro emite certificado (#32): a tela 26 avisa quando há.
    parceiro_nome: str | None = None
    modulos: list[ModuloDetalhe] = []


class TrilhaAtual(Trilha):
    """Card "trilha atual" da home (tela 16)."""

    # Título do primeiro passo que falta. `None` só quando a trilha não tem
    # módulos ainda.
    proximo_modulo: str | None = None


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


class ReporteDoModulo(BaseModel):
    """O resultado de reportar o vídeo de um módulo automático."""

    reportes: int
    # Com reportes suficientes, o módulo saiu da trilha e a lacuna voltou para
    # a busca de conteúdo.
    removido: bool


class ExercicioDePratica(BaseModel):
    enunciado: str
    resposta_esperada: str
    dica: str = ""


class ExerciciosDoPasso(BaseModel):
    """Os exercícios de prática do passo para o nível do aluno (#201).

    Enquanto `status` for `gerando`, a lista vem vazia: pergunte de novo em
    alguns segundos. `sem_conteudo`: o módulo não tem material para gerar.
    """

    status: StatusGeracao
    exercicios: list[ExercicioDePratica]
