"""Leitura de transcrições e divisão do texto em trechos para o embedding.

O trecho é a unidade da busca: pequeno o bastante para o embedding não diluir o
assunto, grande o bastante para fazer sentido sozinho no prompt de uma skill.
Os cortes caem em fim de frase, e cada trecho repete o fim do anterior
(`sobreposicao`), para uma explicação que atravessa o corte não se perder.
"""

import re
from dataclasses import dataclass
from pathlib import PurePath

TAMANHO_DO_TRECHO = 800
SOBREPOSICAO = 150

# "00:01:02,500" (.srt) ou "00:01:02.500" e "01:02.500" (.vtt).
_TEMPO = r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{3})"
_LINHA_DE_TEMPO = re.compile(rf"^\s*{_TEMPO}\s*-->")
# Marcações do WebVTT dentro da fala: <v Professor>, <c.destaque>, <00:01.000>.
_MARCACAO = re.compile(r"<[^>]+>")
_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class Fala:
    texto: str
    # Segundo do vídeo em que a fala começa; `None` em texto sem tempo.
    inicio: float | None = None


@dataclass(frozen=True)
class Trecho:
    texto: str
    inicio: float | None = None


def ler_transcricao(conteudo: str, nome_arquivo: str) -> list[Fala]:
    """As falas do arquivo. `.srt` e `.vtt` guardam o tempo; o resto é texto corrido."""
    extensao = PurePath(nome_arquivo).suffix.lower()
    if extensao in {".srt", ".vtt"}:
        return _ler_legenda(conteudo)
    paragrafos = re.split(r"\n\s*\n", conteudo)
    return [Fala(_espacos(p)) for p in paragrafos if p.strip()]


def _ler_legenda(conteudo: str) -> list[Fala]:
    falas: list[Fala] = []
    for bloco in re.split(r"\n\s*\n", conteudo.replace("\r\n", "\n").lstrip("﻿")):
        linhas = [linha for linha in bloco.split("\n") if linha.strip()]
        tempo = next((i for i, linha in enumerate(linhas) if _LINHA_DE_TEMPO.match(linha)), None)
        # Sem linha de tempo é o cabeçalho "WEBVTT", uma NOTE ou um STYLE.
        if tempo is None:
            continue
        texto = _espacos(_MARCACAO.sub("", " ".join(linhas[tempo + 1 :])))
        if not texto:
            continue
        inicio = _segundos(_LINHA_DE_TEMPO.match(linhas[tempo]))
        # Legendas de vídeo repetem a linha anterior enquanto ela rola na tela.
        if falas and falas[-1].texto == texto:
            continue
        falas.append(Fala(texto, inicio))
    return falas


def _segundos(tempo: re.Match[str] | None) -> float | None:
    if tempo is None:
        return None
    horas, minutos, segundos, milesimos = tempo.groups()
    return int(horas or 0) * 3600 + int(minutos) * 60 + int(segundos) + int(milesimos) / 1000


def _espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def dividir(
    falas: list[Fala], *, tamanho: int = TAMANHO_DO_TRECHO, sobreposicao: int = SOBREPOSICAO
) -> list[Trecho]:
    """Junta as frases em trechos de até `tamanho` caracteres, cortando entre frases."""
    frases = [
        Fala(parte, fala.inicio)
        for fala in falas
        for frase in _FIM_DE_FRASE.split(fala.texto)
        for parte in _quebrar(frase, tamanho)
    ]

    trechos: list[Trecho] = []
    atual: list[Fala] = []
    for frase in frases:
        if atual and _tamanho([*atual, frase]) > tamanho:
            trechos.append(_juntar(atual))
            atual = _cauda(atual, sobreposicao)
            # A cauda mais a frase nova ainda pode estourar: nesse caso, sem
            # sobreposição.
            if _tamanho([*atual, frase]) > tamanho:
                atual = []
        atual.append(frase)
    if atual:
        trechos.append(_juntar(atual))
    return trechos


def _quebrar(frase: str, tamanho: int) -> list[str]:
    """Uma frase maior que o trecho (legenda sem pontuação) é cortada entre palavras."""
    if len(frase) <= tamanho:
        return [frase] if frase.strip() else []
    partes: list[str] = []
    atual = ""
    for palavra in frase.split():
        if atual and len(atual) + 1 + len(palavra) > tamanho:
            partes.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    if atual:
        partes.append(atual)
    return partes


def _tamanho(frases: list[Fala]) -> int:
    return sum(len(f.texto) for f in frases) + max(len(frases) - 1, 0)


def _juntar(frases: list[Fala]) -> Trecho:
    return Trecho(" ".join(f.texto for f in frases), frases[0].inicio)


def _cauda(frases: list[Fala], sobreposicao: int) -> list[Fala]:
    """As últimas frases que cabem em `sobreposicao` caracteres."""
    cauda: list[Fala] = []
    for frase in reversed(frases):
        if _tamanho([frase, *cauda]) > sobreposicao:
            break
        cauda.insert(0, frase)
    return cauda
