"""Skill que diz de que matéria é uma parte de vídeo e quais lacunas ela cobre (#202).

É o controle de qualidade do conteúdo automático: nenhuma pessoa revisa a parte
antes do aluno. A skill classifica a parte, e não o vídeo inteiro, porque uma
aula longa pode passar por assuntos de disciplinas diferentes.

As matérias possíveis vêm de quem chama (as disciplinas das trilhas e das
lacunas), nunca do modelo: `ler_resposta` só aceita uma delas, escrita como na
lista (sem contar acento e caixa), ou "nenhuma". Uma matéria inventada vira
"nenhuma", e a parte é descartada.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from app.ia.base import MensagemIA
from app.ia.skills.ler_ementa import normalizar

MAXIMO_DE_TOKENS = 400
# Caracteres da transcrição da parte que vão no prompt: o bastante para o
# assunto, sem passar do contexto de um modelo pequeno.
TAMANHO_DA_TRANSCRICAO = 3500
NENHUMA = "nenhuma"

PROMPT = """\
Você confere se uma parte de uma aula em vídeo serve para uma trilha de estudos \
de programação.

Você recebe a transcrição da parte, a lista de matérias possíveis e a lista de \
assuntos que procuramos, numerados.

Responda só com JSON, no formato pedido:
- "materia": o nome de uma matéria da lista, escrito como está nela, ou \
"nenhuma" se a parte não for de nenhuma delas.
- "assuntos": os números dos assuntos que a parte ensina de fato. Vazio se não \
ensinar nenhum.
- "confianca": de 0 a 1, o quanto você tem certeza.
- "justificativa": uma frase curta copiada da transcrição que mostra o assunto.

Regras:
- Use só a transcrição. Uma parte que só cita o assunto, sem explicar, não o ensina.
- Nunca responda uma matéria que não está na lista."""


class Resposta(BaseModel):
    materia: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    assuntos: list[int] = []
    confianca: float = Field(ge=0, le=1)
    justificativa: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


FORMATO = Resposta.model_json_schema()


class SaidaInvalida(Exception):
    """A resposta do modelo não é uma `Resposta` válida."""


@dataclass(frozen=True)
class Categoria:
    # `None` quando a resposta foi "nenhuma" ou uma matéria fora da lista.
    materia: str | None
    # Índices (a partir de 0) dos assuntos da lista que a parte cobre.
    assuntos: list[int]
    confianca: float
    justificativa: str


def mensagens(
    transcricao: str, materias: Sequence[str], assuntos: Sequence[str]
) -> list[MensagemIA]:
    lista_materias = "\n".join(f"- {m}" for m in materias)
    lista_assuntos = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(assuntos)) or "(nenhum)"
    pedido = (
        f"Matérias possíveis:\n{lista_materias}\n\n"
        f"Assuntos procurados:\n{lista_assuntos}\n\n"
        f"Transcrição da parte:\n{transcricao[:TAMANHO_DA_TRANSCRICAO]}"
    )
    return [MensagemIA("system", PROMPT), MensagemIA("user", pedido)]


def ler_resposta(resposta: str, materias: Sequence[str], total_de_assuntos: int) -> Categoria:
    """A resposta validada contra as listas dadas. Levanta `SaidaInvalida`."""
    sem_cerca = re.sub(r"^\s*```(?:json)?|```\s*$", "", resposta.strip())
    try:
        dados = Resposta.model_validate(json.loads(sem_cerca))
    except (json.JSONDecodeError, ValidationError) as erro:
        raise SaidaInvalida(str(erro)) from erro

    por_chave = {normalizar(m): m for m in materias}
    materia = por_chave.get(normalizar(dados.materia))
    # O modelo numera a partir de 1; fora da lista, o número é descartado.
    assuntos = sorted({n - 1 for n in dados.assuntos if 1 <= n <= total_de_assuntos})
    return Categoria(
        materia=materia,
        assuntos=assuntos if materia else [],
        confianca=dados.confianca,
        justificativa=dados.justificativa,
    )
