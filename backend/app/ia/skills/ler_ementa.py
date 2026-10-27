"""Skill que lê o texto da ementa e devolve as disciplinas e os assuntos (#38).

O texto vem do PDF, já extraído (`services/ementas.py`). Uma ementa de curso
inteiro passa de dezenas de páginas e não cabe no contexto de um modelo pequeno,
então ela vai em partes (`dividir_texto`), uma chamada por parte, e as leituras
se juntam no fim (`juntar`): a mesma disciplina partida entre duas partes vira
uma só.

A resposta é JSON no formato de `Leitura`, pedido ao provedor pelo `FORMATO`.
O que não valida é descartado inteiro (`SaidaInvalida`): uma disciplina pela
metade levaria o aluno a uma trilha errada sem ninguém perceber.
"""

import json
import re
import unicodedata
from collections.abc import Sequence
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from app.ia.base import MensagemIA

# Em caracteres. Com o prompt e a resposta, cabe no contexto padrão do Ollama
# (4096 tokens) com folga.
TAMANHO_DA_PARTE = 4000

# A resposta de uma parte: algumas disciplinas, cada uma com uma lista curta.
MAXIMO_DE_TOKENS = 2000

PROMPT = """\
Você lê ementas de cursos de graduação e extrai o conteúdo programático.

Responda só com JSON, no formato pedido:
- "disciplinas": cada disciplina que aparece no texto, na ordem do documento.
- "nome": o nome da disciplina como está no texto, sem o código.
- "periodo" e "carga_horaria" (em horas): só se estiverem no texto; senão, null.
- "assuntos": os tópicos do conteúdo programático, cada um curto (até oito \
palavras), em português, sem numeração. Um tópico com subtópicos vira um \
assunto por subtópico.

Regras:
- Use só o que está no texto. Não complete com o que costuma cair na disciplina.
- Ignore bibliografia, objetivos, metodologia, avaliação e nomes de professores.
- O texto pode ser só um pedaço da ementa: extraia o que houver nele. Sem \
disciplina no pedaço, responda {"disciplinas": []}."""

Assunto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class Disciplina(BaseModel):
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    periodo: int | None = Field(default=None, ge=1, le=20)
    carga_horaria: int | None = Field(default=None, ge=1, le=2000)
    assuntos: list[Assunto] = []


class Leitura(BaseModel):
    disciplinas: list[Disciplina]


# JSON Schema da resposta, para o provedor restringir a geração a ele.
FORMATO = Leitura.model_json_schema()


class SaidaInvalida(Exception):
    """A resposta do modelo não é uma `Leitura` válida."""


def dividir_texto(texto: str, *, tamanho: int = TAMANHO_DA_PARTE) -> list[str]:
    """O texto em partes de até `tamanho` caracteres, cortando entre linhas."""
    partes: list[str] = []
    atual: list[str] = []
    ocupado = 0
    for linha in (linha.strip() for linha in texto.splitlines()):
        if not linha:
            continue
        # Uma linha sozinha maior que a parte (PDF sem quebra) é cortada seca.
        pedacos = [linha[i : i + tamanho] for i in range(0, len(linha), tamanho)]
        for pedaco in pedacos:
            if atual and ocupado + 1 + len(pedaco) > tamanho:
                partes.append("\n".join(atual))
                atual, ocupado = [], 0
            atual.append(pedaco)
            ocupado += len(pedaco) + (1 if ocupado else 0)
    if atual:
        partes.append("\n".join(atual))
    return partes


def mensagens(parte: str) -> list[MensagemIA]:
    return [MensagemIA("system", PROMPT), MensagemIA("user", f"Texto da ementa:\n\n{parte}")]


def ler_resposta(resposta: str) -> Leitura:
    """A resposta do modelo validada. Levanta `SaidaInvalida`."""
    # Mesmo com o formato pedido, um modelo às vezes embrulha o JSON em ```.
    sem_cerca = re.sub(r"^\s*```(?:json)?|```\s*$", "", resposta.strip())
    try:
        return Leitura.model_validate(json.loads(sem_cerca))
    except (json.JSONDecodeError, ValidationError) as erro:
        raise SaidaInvalida(str(erro)) from erro


def juntar(leituras: Sequence[Leitura]) -> list[Disciplina]:
    """Uma disciplina por nome, com os assuntos na ordem e sem repetição.

    A disciplina que atravessa o corte entre duas partes aparece nas duas
    leituras: os assuntos se somam, e o período e a carga horária ficam com o
    primeiro que veio preenchido.
    """
    juntas: dict[str, Disciplina] = {}
    for leitura in leituras:
        for disciplina in leitura.disciplinas:
            chave = normalizar(disciplina.nome)
            if not chave:
                continue
            atual = juntas.setdefault(chave, Disciplina(nome=disciplina.nome))
            atual.periodo = atual.periodo or disciplina.periodo
            atual.carga_horaria = atual.carga_horaria or disciplina.carga_horaria
            vistos = {normalizar(a) for a in atual.assuntos}
            for assunto in disciplina.assuntos:
                if normalizar(assunto) not in vistos:
                    vistos.add(normalizar(assunto))
                    atual.assuntos.append(assunto)
    return list(juntas.values())


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e só com letras e números separados por espaço."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", sem_acento.lower()))
