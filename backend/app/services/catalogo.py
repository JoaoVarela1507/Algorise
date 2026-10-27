"""Catálogo acadêmico do onboarding (telas 14 e 15): instituições, cursos e períodos.

Só entra aqui o que é **verificado** (veio do seed). O que o aluno digita
livremente continua sendo gravado no perfil dele (`services/perfil.py`), mas não
vira sugestão: um "ufrpee" com erro de digitação não pode aparecer no
autocomplete de todo mundo.

A busca roda em Python, e não no banco, de propósito. Tolerar acento e erro de
digitação no PostgreSQL pede as extensões `unaccent` e `pg_trgm`, que a suíte em
SQLite não tem — e o catálogo verificado é pequeno (dezenas de instituições),
então trazê-lo inteiro custa menos que manter duas implementações da busca.
Se ele crescer para milhares, é aqui que entra o `pg_trgm`.
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Curso, Instituicao, Trilha

# Abaixo disto, a semelhança é coincidência e não erro de digitação. Com 0.75,
# "pernanbuco" acha "pernambuco" e "ufrp" acha "ufrpe", mas "ufpb" não acha
# "ufrpe".
SEMELHANCA_MINIMA = 0.75

# Palavras que aparecem em quase todo nome e não ajudam a distinguir.
_PALAVRAS_VAZIAS = {"de", "da", "do", "das", "dos", "e"}


@dataclass(frozen=True)
class Periodo:
    numero: int
    disciplinas: list[str]


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e só com letras e números separados por espaço."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", sem_acento.lower()))


def buscar_instituicoes(db: Session, busca: str, *, limite: int = 10) -> list[Instituicao]:
    """Instituições verificadas que casam com o que o aluno digitou, melhores primeiro.

    Sem busca, devolve as primeiras em ordem alfabética, para a lista não abrir
    vazia.
    """
    verificadas = (
        db.execute(
            select(Instituicao).where(Instituicao.verificada.is_(True)).order_by(Instituicao.nome)
        )
        .scalars()
        .all()
    )

    termos = [t for t in normalizar(busca).split() if t not in _PALAVRAS_VAZIAS]
    if not termos:
        return list(verificadas[:limite])

    pontuadas = [
        (pontuacao, instituicao)
        for instituicao in verificadas
        if (pontuacao := _pontuar(termos, instituicao)) >= SEMELHANCA_MINIMA
    ]
    pontuadas.sort(key=lambda par: (-par[0], par[1].nome))
    return [instituicao for _, instituicao in pontuadas[:limite]]


def obter_instituicao_verificada(db: Session, instituicao_id: int) -> Instituicao | None:
    instituicao = db.get(Instituicao, instituicao_id)
    return instituicao if instituicao is not None and instituicao.verificada else None


def cursos_da_instituicao(db: Session, instituicao_id: int) -> list[Curso]:
    return list(
        db.execute(
            select(Curso)
            .where(Curso.instituicao_id == instituicao_id, Curso.verificado.is_(True))
            .order_by(Curso.nome)
        ).scalars()
    )


def obter_curso_verificado(db: Session, curso_id: int) -> Curso | None:
    curso = db.get(Curso, curso_id)
    return curso if curso is not None and curso.verificado else None


def periodos_do_curso(db: Session, curso: Curso) -> list[Periodo]:
    """Cada período do curso com as disciplinas que o Algorise cobre nele.

    "Conhecidas" quer dizer: há trilha publicada para elas naquele período. A
    grade de cada curso (o que a faculdade pede, disciplina por disciplina) só
    existe quando a ementa do aluno é lida (#38); até lá, o que dá para mostrar
    com honestidade é o que o catálogo tem para estudar.
    """
    linhas = db.execute(
        select(Trilha.periodo, Trilha.disciplina)
        .where(Trilha.publicada.is_(True), Trilha.periodo.is_not(None))
        .distinct()
    ).all()

    por_periodo: dict[int, set[str]] = {}
    for numero, disciplina in linhas:
        por_periodo.setdefault(numero, set()).add(disciplina)

    return [
        Periodo(numero=numero, disciplinas=sorted(por_periodo.get(numero, set())))
        for numero in range(1, curso.total_periodos + 1)
    ]


def _pontuar(termos: list[str], instituicao: Instituicao) -> float:
    """De 0 a 1: quanto o que foi digitado casa com o nome ou a sigla.

    Cada termo vale a melhor nota que tirar contra alguma palavra do nome. Nota 1
    é a palavra começar pelo termo ("pern" em "pernambuco"); abaixo disso, a
    semelhança de caracteres, que é o que pega o erro de digitação. A nota final é
    a do pior termo: "rural paraiba" não deve achar a Rural de Pernambuco só
    porque "rural" casou.
    """
    palavras = [p for p in normalizar(instituicao.nome).split() if p not in _PALAVRAS_VAZIAS]
    if instituicao.sigla:
        palavras.append(normalizar(instituicao.sigla))

    return min(max(_nota(termo, palavra) for palavra in palavras) for termo in termos)


def _nota(termo: str, palavra: str) -> float:
    if palavra.startswith(termo):
        return 1.0
    # Comparar com o começo da palavra, do tamanho do termo (com folga de um),
    # faz "ufrp" contra "ufrpe" e "pernanb" contra "pernambuco" contarem como
    # digitação incompleta com erro, e não como palavras diferentes.
    trecho = palavra[: len(termo) + 1]
    return max(
        SequenceMatcher(None, termo, palavra).ratio(),
        SequenceMatcher(None, termo, trecho).ratio(),
    )
