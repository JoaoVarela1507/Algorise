"""Busca por similaridade no vault, a porta de entrada das skills (#200)."""

import math
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.ia.base import ProvedorIA
from app.models import DocumentoVault, Modulo, OrigemVault, TrechoVault, Trilha


@dataclass(frozen=True)
class Resultado:
    texto: str
    # Distância de cosseno: 0 é o mesmo sentido, 2 é o oposto.
    distancia: float
    chave: str
    titulo: str
    origem: OrigemVault
    modulo_id: int | None
    inicio_segundos: float | None


async def buscar(
    sessao: Session,
    provedor: ProvedorIA,
    texto: str,
    *,
    trilha_id: int | None = None,
    disciplina: str | None = None,
    origem: OrigemVault | None = None,
    limite: int = 5,
) -> list[Resultado]:
    """Os `limite` trechos mais próximos de `texto`, do mais para o menos parecido.

    `trilha_id` e `disciplina` valem para as transcrições, que estão ligadas a
    um módulo; filtrar por eles deixa os prompts de fora.
    """
    [vetor] = await provedor.embeddings([texto])

    consulta = select(TrechoVault, DocumentoVault).join(TrechoVault.documento)
    if trilha_id is not None or disciplina is not None:
        consulta = consulta.join(Modulo, DocumentoVault.modulo_id == Modulo.id)
    if trilha_id is not None:
        consulta = consulta.where(Modulo.trilha_id == trilha_id)
    if disciplina is not None:
        consulta = consulta.join(Trilha, Modulo.trilha_id == Trilha.id).where(
            func.lower(Trilha.disciplina) == disciplina.lower()
        )
    if origem is not None:
        consulta = consulta.where(DocumentoVault.origem == origem)

    if sessao.get_bind().dialect.name == "postgresql":
        linhas = _no_pgvector(sessao, consulta, vetor, limite)
    else:
        linhas = _em_python(sessao, consulta, vetor, limite)
    return [
        Resultado(
            texto=trecho.texto,
            distancia=distancia,
            chave=documento.chave,
            titulo=documento.titulo,
            origem=documento.origem,
            modulo_id=documento.modulo_id,
            inicio_segundos=trecho.inicio_segundos,
        )
        for trecho, documento, distancia in linhas
    ]


def _no_pgvector(
    sessao: Session, consulta: Select, vetor: list[float], limite: int
) -> list[tuple[TrechoVault, DocumentoVault, float]]:
    distancia = TrechoVault.embedding.cosine_distance(vetor)
    linhas = sessao.execute(consulta.add_columns(distancia).order_by(distancia).limit(limite))
    return [(trecho, documento, float(d)) for trecho, documento, d in linhas]


def _em_python(
    sessao: Session, consulta: Select, vetor: list[float], limite: int
) -> list[tuple[TrechoVault, DocumentoVault, float]]:
    """O SQLite dos testes não tem pgvector: a distância é calculada aqui."""
    linhas = [
        (trecho, documento, distancia_cosseno(vetor, trecho.embedding))
        for trecho, documento in sessao.execute(consulta)
    ]
    return sorted(linhas, key=lambda linha: linha[2])[:limite]


def distancia_cosseno(a: list[float], b: list[float]) -> float:
    """A mesma conta do operador `<=>` do pgvector."""
    norma = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norma == 0:
        return 1.0
    return 1 - sum(x * y for x, y in zip(a, b, strict=True)) / norma
