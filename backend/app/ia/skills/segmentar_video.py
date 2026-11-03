"""Skill que corta uma aula longa em partes de um assunto só (#209).

Cada parte vira um módulo da trilha (#210). Não há edição de vídeo: a parte é um
par de tempos, que o player incorporado do YouTube aceita (`?start=&end=`).

O modelo não recebe a transcrição inteira, que numa aula de uma hora passa do
contexto de um modelo pequeno: recebe um índice, uma linha por trecho do vault
com o intervalo e o começo do texto (`indice`). E o que ele devolve não vai
direto para o banco: `ajustar` põe as partes em ordem, encosta uma na outra e
leva cada corte para a fronteira de fala mais próxima, porque um modelo pequeno
erra segundos e às vezes sobrepõe partes. Se a resposta não valida, quem chama
corta por duração (`por_duracao`), sem IA.
"""

import json
import re
from collections.abc import Sequence
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from app.ia.base import MensagemIA
from app.ia.vault.trechos import Trecho

MAXIMO_DE_TOKENS = 1500
# Linhas do índice: acima disto, trechos vizinhos se juntam numa linha só.
LINHAS_DO_INDICE = 60
# Caracteres de cada trecho que entram na linha do índice.
COMECO_DO_TRECHO = 120

PROMPT = """\
Você divide aulas em vídeo em partes, cada uma sobre um assunto só, para virarem \
módulos de uma trilha de estudos.

Você recebe o título da aula e um índice da transcrição: cada linha tem o \
intervalo, em segundos, e o começo do que é dito ali.

Responda só com JSON, no formato pedido:
- "partes": em ordem, cada uma com "inicio" e "fim" (em segundos, tirados do \
índice), "titulo" (curto, até oito palavras, em português) e "resumo" (uma \
frase sobre o que a parte ensina).

Regras:
- Corte onde o assunto muda, não no meio de uma explicação.
- Cada parte tem no máximo {maximo} minutos.
- Pule a introdução e o encerramento que não ensinam nada (apresentação, \
pedido de inscrição no canal).
- Use só o que está no índice. Não invente assunto."""

Titulo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Resumo = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class Parte(BaseModel):
    inicio: float = Field(ge=0)
    fim: float = Field(gt=0)
    titulo: Titulo
    resumo: Resumo = ""


class Segmentacao(BaseModel):
    partes: list[Parte] = Field(min_length=1, max_length=30)


FORMATO = Segmentacao.model_json_schema()


class SaidaInvalida(Exception):
    """A resposta do modelo não é uma `Segmentacao` válida."""


def indice(trechos: Sequence[Trecho]) -> str:
    """Uma linha por trecho: `[120-310] começo do texto…`, juntando vizinhos se forem muitos."""
    grupos = max(1, -(-len(trechos) // LINHAS_DO_INDICE))
    linhas = []
    for inicio in range(0, len(trechos), grupos):
        grupo = trechos[inicio : inicio + grupos]
        comeco = " ".join(t.texto for t in grupo)[:COMECO_DO_TRECHO]
        linhas.append(f"[{_seg(grupo[0].inicio)}-{_seg(grupo[-1].fim)}] {comeco}")
    return "\n".join(linhas)


def mensagens(titulo: str, trechos: Sequence[Trecho], *, maximo_minutos: int) -> list[MensagemIA]:
    return [
        MensagemIA("system", PROMPT.format(maximo=maximo_minutos)),
        MensagemIA("user", f"Título da aula: {titulo}\n\nÍndice:\n{indice(trechos)}"),
    ]


def ler_resposta(resposta: str) -> Segmentacao:
    sem_cerca = re.sub(r"^\s*```(?:json)?|```\s*$", "", resposta.strip())
    try:
        return Segmentacao.model_validate(json.loads(sem_cerca))
    except (json.JSONDecodeError, ValidationError) as erro:
        raise SaidaInvalida(str(erro)) from erro


def ajustar(partes: Sequence[Parte], fronteiras: Sequence[float], duracao: float) -> list[Parte]:
    """As partes em ordem, dentro do vídeo, encostadas e com os cortes nas fronteiras de fala.

    `fronteiras` são os segundos em que uma fala começa (e o fim do vídeo). A
    primeira parte pode começar depois do zero e a última terminar antes do
    fim (a introdução e o encerramento descartados); entre elas, não sobra
    buraco nem sobreposição. Levanta `SaidaInvalida` se nada sobrar.
    """
    pontos = sorted({0.0, *fronteiras, duracao})
    ordenadas = sorted(partes, key=lambda p: p.inicio)
    cortes = [_mais_perto(pontos, p.inicio) for p in ordenadas]
    fim_da_ultima = _mais_perto(pontos, min(ordenadas[-1].fim, duracao)) if ordenadas else 0
    ajustadas = []
    for i, parte in enumerate(ordenadas):
        inicio = cortes[i]
        fim = cortes[i + 1] if i + 1 < len(ordenadas) else fim_da_ultima
        # Duas partes que caíram no mesmo corte viram uma: a de antes some.
        if fim <= inicio:
            continue
        ajustadas.append(parte.model_copy(update={"inicio": inicio, "fim": fim}))
    if not ajustadas:
        raise SaidaInvalida("Nenhuma parte sobrou depois do ajuste")
    return ajustadas


def por_duracao(
    titulo: str, fronteiras: Sequence[float], duracao: float, *, maximo_segundos: float
) -> list[Parte]:
    """Partes de até `maximo_segundos`, cortadas na fronteira de fala, sem IA.

    É o que sobra quando o modelo não responde direito: o aluno perde o título
    de cada parte ("Parte 2"), mas não perde a aula.
    """
    pontos = sorted({0.0, *(f for f in fronteiras if 0 < f < duracao), duracao})
    partes: list[Parte] = []
    inicio = 0.0
    anterior = 0.0
    for ponto in pontos[1:]:
        if ponto - inicio > maximo_segundos and anterior > inicio:
            partes.append(_parte(titulo, len(partes) + 1, inicio, anterior))
            inicio = anterior
        anterior = ponto
    partes.append(_parte(titulo, len(partes) + 1, inicio, duracao))
    if len(partes) == 1:
        return [partes[0].model_copy(update={"titulo": titulo[:120]})]
    return partes


def _parte(titulo: str, numero: int, inicio: float, fim: float) -> Parte:
    return Parte(inicio=inicio, fim=fim, titulo=f"{titulo[:100]} (parte {numero})")


def _mais_perto(pontos: Sequence[float], alvo: float) -> float:
    return min(pontos, key=lambda ponto: abs(ponto - alvo))


def _seg(valor: float | None) -> str:
    return "?" if valor is None else str(round(valor))
