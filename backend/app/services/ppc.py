"""Onde, num PPC, estão as ementas das disciplinas.

O aluno envia o PPC (Projeto Pedagógico do Curso) como "ementa": um documento de
100 a 300 páginas em que as ementas das disciplinas ocupam um capítulo só, o
ementário. Mandar o resto para a IA (histórico do curso, perfil do egresso,
infraestrutura) custaria dezenas de chamadas e ainda poderia inventar
"assuntos" a partir de texto que não é conteúdo programático.

`localizar` tenta, do mais confiável para o menos:

1. **Marcadores do PDF** (o índice lateral): o item cujo título fala em ementa
   vai da página dele até a do próximo item.
2. **Sumário** nas primeiras páginas: a linha `EMENTÁRIO ........ 87`. O número
   impresso costuma não ser o da página no PDF (capa e sumário não contam), então
   o início é a página, depois do sumário, em que o título aparece como
   cabeçalho; o tamanho do trecho vem da diferença para a entrada seguinte.
3. **Densidade**: o trecho contínuo de páginas com cara de ementa ("Ementa",
   "Carga horária", "Bibliografia básica").

Sem nada disso, o documento inteiro: é o caso de uma ementa de verdade, curta,
que não precisa de recorte.

As páginas são índices a partir de 0, e o fim é inclusivo.
"""

import re
import unicodedata
from dataclasses import dataclass

# Quantas páginas do começo podem ter o sumário.
PAGINAS_DO_SUMARIO = 15

# Título de capítulo de ementas, já sem acento e em minúsculas: "Ementário",
# "Ementas das disciplinas", "Ementário dos componentes curriculares".
_TITULO = re.compile(r"\bement(ario|as)\b")
# Linha de sumário: título, pontilhado ou espaço, número da página no fim.
_LINHA_DO_SUMARIO = re.compile(r"^(?P<titulo>.*?\w.*?)[\s.·_-]*\.{2,}[\s.]*(?P<pagina>\d{1,4})\s*$")
# O pypdf costuma juntar o pontilhado em espaço: "EMENTÁRIO 87".
_LINHA_SEM_PONTILHADO = re.compile(r"^(?P<titulo>[^.]*?[a-z][^.]*?)\s+(?P<pagina>\d{1,4})\s*$")
# Uma frase do texto que termina em número não é entrada de sumário.
_TITULO_MAXIMO = 80
# O que aparece numa página de ementário.
_MARCAS = [
    re.compile(r"\bementa\b"),
    re.compile(r"carga horaria"),
    re.compile(r"bibliografia (basica|complementar)"),
    re.compile(r"pre-? ?requisito"),
]
# Uma página do ementário tem pelo menos duas das marcas.
_MINIMO_DE_MARCAS = 2


@dataclass(frozen=True)
class Trecho:
    inicio: int
    fim: int
    # Como foi achado: "marcadores", "sumario", "densidade" ou "documento".
    metodo: str


def localizar(paginas: list[str], marcadores: list[tuple[str, int]] | None = None) -> Trecho:
    """O trecho do ementário, ou o documento inteiro se ele não for achado.

    `marcadores` são os itens do índice lateral do PDF, em ordem: título e
    página.
    """
    total = len(paginas)
    normalizadas = [_normalizar(p) for p in paginas]
    return (
        _pelos_marcadores(marcadores or [], total)
        or _pelo_sumario(normalizadas)
        or _pela_densidade(normalizadas)
        or Trecho(0, max(total - 1, 0), "documento")
    )


def _pelos_marcadores(marcadores: list[tuple[str, int]], total: int) -> Trecho | None:
    for i, (titulo, pagina) in enumerate(marcadores):
        if not _TITULO.search(_normalizar(titulo)):
            continue
        # O próximo item que começa depois dele fecha o trecho.
        seguinte = next((p for _, p in marcadores[i + 1 :] if p > pagina), total)
        return Trecho(pagina, seguinte - 1, "marcadores")
    return None


def _pelo_sumario(paginas: list[str]) -> Trecho | None:
    entradas = _entradas_do_sumario(paginas[:PAGINAS_DO_SUMARIO])
    for i, (titulo, impressa, pagina_do_sumario) in enumerate(entradas):
        if not _TITULO.search(titulo):
            continue
        inicio = _cabecalho(paginas, titulo, depois_de=pagina_do_sumario)
        if inicio is None:
            # Sem o cabeçalho para medir o deslocamento, o número impresso é o
            # melhor palpite. Fora do documento, a entrada não serve.
            inicio = impressa - 1
            if not pagina_do_sumario < inicio < len(paginas):
                continue
        seguinte = next((p for _, p, _ in entradas[i + 1 :] if p > impressa), None)
        fim = len(paginas) - 1 if seguinte is None else inicio + (seguinte - impressa) - 1
        return Trecho(inicio, min(fim, len(paginas) - 1), "sumario")
    return None


def _entradas_do_sumario(paginas: list[str]) -> list[tuple[str, int, int]]:
    """Título, página impressa e a página do PDF em que a linha do sumário está."""
    entradas = []
    for indice, texto in enumerate(paginas):
        for linha in texto.splitlines():
            achou = _LINHA_DO_SUMARIO.match(linha.strip()) or _LINHA_SEM_PONTILHADO.match(
                linha.strip()
            )
            if achou:
                titulo = re.sub(r"^[\d.\s]+", "", achou["titulo"]).strip(" .")
                if 0 < len(titulo) <= _TITULO_MAXIMO:
                    entradas.append((titulo, int(achou["pagina"]), indice))
    return entradas


def _cabecalho(paginas: list[str], titulo: str, *, depois_de: int) -> int | None:
    """A primeira página depois do sumário com uma linha que é o título."""
    for indice in range(depois_de + 1, len(paginas)):
        for linha in paginas[indice].splitlines():
            limpa = re.sub(r"^[\d.\s]+", "", linha).strip(" .")
            if limpa == titulo:
                return indice
    return None


def _pela_densidade(paginas: list[str]) -> Trecho | None:
    """O maior trecho de páginas de ementa, tolerando uma página solta no meio."""
    eh_ementa = [sum(1 for m in _MARCAS if m.search(p)) >= _MINIMO_DE_MARCAS for p in paginas]
    melhor: tuple[int, int] | None = None
    inicio: int | None = None
    ultima = -2
    for indice, sim in enumerate(eh_ementa):
        if not sim:
            continue
        # Até uma página sem marca entre duas com marca continua o trecho.
        if inicio is None or indice - ultima > 2:
            inicio = indice
        ultima = indice
        if melhor is None or ultima - inicio > melhor[1] - melhor[0]:
            melhor = (inicio, ultima)
    # Uma página só não é um ementário: pode ser a ementa de uma disciplina
    # citada no meio do texto.
    if melhor is None or melhor[1] == melhor[0]:
        return None
    return Trecho(melhor[0], melhor[1], "densidade")


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()
