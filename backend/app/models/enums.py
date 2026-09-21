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


class OrigemXP(str, Enum):
    atividade = "atividade"
    modulo = "modulo"
    trilha = "trilha"
    desafio = "desafio"
