"""Skill que cria exercícios de prática a partir do conteúdo de um módulo (#201).

O exercício tem de cobrir o que o vídeo e o módulo ensinaram, no nível do aluno.
Por isso o prompt leva só os trechos do vault daquele módulo (a transcrição, ou
o pedaço dela no módulo que é um intervalo de uma aula longa, e a descrição), e
quem chama não gera nada quando não há trecho: um exercício sem conteúdo seria
inventado pelo modelo.

A resposta é JSON no formato de `Lista`; o que não valida é descartado inteiro.
"""

import json
import re
from collections.abc import Sequence
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from app.ia.base import MensagemIA
from app.models.enums import NivelExperiencia

QUANTIDADE = 3
MAXIMO_DE_TOKENS = 1500
# Caracteres do conteúdo do módulo que vão no prompt.
TAMANHO_DO_CONTEUDO = 5000

DESCRICAO_DO_NIVEL = {
    NivelExperiencia.baixo: "está começando a programar: exercícios diretos, um conceito por vez",
    NivelExperiencia.medio: "já programa um pouco: exercícios que juntam dois conceitos",
    NivelExperiencia.alto: "programa com segurança: exercícios com raciocínio e casos de borda",
}

PROMPT = """\
Você cria exercícios de prática para uma plataforma que ensina programação a \
estudantes de graduação, em português do Brasil.

Você recebe o título do módulo, o nível do aluno e o conteúdo que o módulo \
ensinou (a transcrição do vídeo e a descrição).

Responda só com JSON, no formato pedido:
- "exercicios": {quantidade} exercícios, cada um com "enunciado" (o que o aluno \
deve fazer), "resposta_esperada" (a resposta ou o código que resolve) e "dica" \
(uma pista que ajuda sem entregar a resposta).

Regras:
- Use só o que está no conteúdo. Não cobre assunto que o módulo não ensinou.
- Código em Python, curto, em blocos Markdown com a linguagem indicada.
- Ajuste a dificuldade ao nível do aluno."""


class Exercicio(BaseModel):
    enunciado: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)
    ]
    resposta_esperada: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)
    ]
    dica: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class Lista(BaseModel):
    exercicios: list[Exercicio] = Field(min_length=1, max_length=10)


FORMATO = Lista.model_json_schema()


class SaidaInvalida(Exception):
    """A resposta do modelo não é uma `Lista` válida."""


def mensagens(
    titulo: str,
    nivel: NivelExperiencia,
    conteudo: Sequence[str],
    *,
    quantidade: int = QUANTIDADE,
) -> list[MensagemIA]:
    texto = "\n\n".join(conteudo)[:TAMANHO_DO_CONTEUDO]
    pedido = (
        f"Módulo: {titulo}\n"
        f"Nível do aluno: {DESCRICAO_DO_NIVEL[nivel]}.\n\n"
        f"Conteúdo do módulo:\n{texto}"
    )
    return [
        MensagemIA("system", PROMPT.format(quantidade=quantidade)),
        MensagemIA("user", pedido),
    ]


def ler_resposta(resposta: str) -> Lista:
    sem_cerca = re.sub(r"^\s*```(?:json)?|```\s*$", "", resposta.strip())
    try:
        return Lista.model_validate(json.loads(sem_cerca))
    except (json.JSONDecodeError, ValidationError) as erro:
        raise SaidaInvalida(str(erro)) from erro
