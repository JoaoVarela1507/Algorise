"""Enums de domínio.

Ficam num lugar só e são reaproveitados pelos modelos e pelos schemas Pydantic,
para o banco e a API nunca discordarem sobre os valores aceitos.
"""

from enum import Enum


class NivelExperiencia(str, Enum):
    """Perfil escolhido no onboarding (telas 7 a 9)."""

    baixo = "baixo"
    medio = "medio"
    alto = "alto"


class TipoTrilha(str, Enum):
    """Modalidade de trilha (telas 10 a 13)."""

    guiada = "guiada"
    livre = "livre"
    mista = "mista"


class TamanhoFonte(str, Enum):
    """Preferência de acessibilidade das telas 18 e 19."""

    normal = "normal"
    alta = "alta"


class TipoAtividade(str, Enum):
    """Formato da atividade dentro de um módulo (telas 28 a 34)."""

    terminal = "terminal"
    resposta_aberta = "resposta-aberta"
    multipla_escolha = "multipla-escolha"
    ordenacao = "ordenacao"
    preencher_lacuna = "preencher-lacuna"
    desafio_codigo = "desafio-codigo"


class StatusProgresso(str, Enum):
    bloqueado = "bloqueado"
    em_andamento = "em-andamento"
    concluido = "concluido"


class StatusEmenta(str, Enum):
    """Processamento do PDF enviado no onboarding (telas 14 e 15)."""

    pendente = "pendente"
    processando = "processando"
    processada = "processada"
    falhou = "falhou"


class StatusAssuntos(str, Enum):
    """Leitura das disciplinas e dos assuntos da ementa pela IA (#38).

    Vem depois da extração do texto e tem status próprio: a ementa pode estar
    `processada` (o texto existe) com os assuntos ainda na fila, ou com a IA
    fora do ar.
    """

    pendente = "pendente"
    processando = "processando"
    prontos = "prontos"
    falhou = "falhou"


class StatusLacuna(str, Enum):
    """Assunto de ementa que o catálogo ainda não cobre (#38).

    `pendente` espera a busca de conteúdo (#207); `em_preparacao` já tem vídeo
    sendo transcrito; `coberta` virou módulo; `sem_conteudo` a busca não achou
    nada aproveitável.
    """

    pendente = "pendente"
    em_preparacao = "em_preparacao"
    coberta = "coberta"
    sem_conteudo = "sem_conteudo"


class OrigemXP(str, Enum):
    atividade = "atividade"
    modulo = "modulo"
    trilha = "trilha"
    desafio = "desafio"


class PapelMensagem(str, Enum):
    """Quem escreveu a mensagem do chat (telas 21 a 23)."""

    usuario = "usuario"
    assistente = "assistente"


class ModoResposta(str, Enum):
    """Quanto o tutor se aprofunda (seletor do campo de mensagem, tela 21)."""

    rapido = "rapido"
    medio = "medio"
    detalhado = "detalhado"


class OrigemVault(str, Enum):
    """De onde veio um documento do vault das skills (#200)."""

    transcricao = "transcricao"
    prompt = "prompt"
    # Título e descrição de um módulo do catálogo: é o que deixa a ementa (#38)
    # achar um módulo que ainda não tem transcrição.
    modulo = "modulo"
