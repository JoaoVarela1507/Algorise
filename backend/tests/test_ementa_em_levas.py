"""Leitura da ementa em duas levas e resistente a parte inválida.

O texto é dividido em partes, e cada parte é uma chamada ao modelo, que na CPU
leva minutos. As partes com cara de programação vão primeiro: com elas, os
assuntos ficam prontos e o aluno já revisa. O resto vem depois, na mesma tarefa.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Sequence
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.ia import IAIndisponivel, MensagemIA
from app.ia.skills import ler_ementa
from app.models import Ementa, StatusAssuntos, StatusEmenta, Usuario
from app.services import assuntos_ementa, ementas
from tests.test_ementa_assuntos import vetor_por_tema

PROGRAMACAO = "Algoritmos e Programação: variáveis, condicionais, laços"
CALCULO = "Cálculo I: limites e derivadas"
ETICA = "Ética e sociedade"


def leitura(nome: str, programacao: bool, *assuntos: str) -> str:
    disciplina = {"nome": nome, "programacao": programacao, "assuntos": list(assuntos)}
    return json.dumps({"disciplinas": [disciplina]})


RESPOSTAS = {
    PROGRAMACAO: leitura("Algoritmos", True, "Variáveis e tipos", "Laços de repetição"),
    CALCULO: leitura("Cálculo I", False, "Limites", "Derivadas"),
    ETICA: leitura("Ética", False, "Ética profissional"),
}


class ProvedorPorParte:
    """Responde pela parte recebida e anota a ordem e o estado da ementa a cada chamada."""

    def __init__(self, fabrica: sessionmaker[Session], ementa_id: int) -> None:
        self.fabrica = fabrica
        self.ementa_id = ementa_id
        self.respostas = dict(RESPOSTAS)
        self.lidas: list[str] = []
        self.estados: list[tuple[str, int]] = []
        self.fora_em: str | None = None

    async def gerar(
        self, mensagens: Sequence[MensagemIA], *, max_tokens: int, formato: Any = None
    ) -> AsyncGenerator[str]:
        parte = mensagens[-1].conteudo.removeprefix("Texto da ementa:\n\n")
        self.lidas.append(parte)
        with self.fabrica() as db:
            ementa = db.get_one(Ementa, self.ementa_id)
            self.estados.append((ementa.status_assuntos.value, ementa.partes_pendentes))
        if parte == self.fora_em:
            raise IAIndisponivel("fora (simulado)")
        yield self.respostas[parte]

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        return [vetor_por_tema(texto) for texto in textos]


@pytest.fixture
def ementa(db: Session, usuario: Usuario) -> Ementa:
    registro = Ementa(
        usuario_id=usuario.id,
        arquivo_path="x.pdf",
        status=StatusEmenta.processada,
        texto_extraido="ignorado: as partes vêm do monkeypatch",
    )
    db.add(registro)
    db.commit()
    return registro


def ler(
    db: Session,
    ementa: Ementa,
    provedor: ProvedorPorParte,
    partes: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assuntos_ementa, "_partes", lambda _: partes)
    asyncio.run(assuntos_ementa.processar(db, provedor, ementa))
    db.refresh(ementa)


def nomes(ementa: Ementa) -> list[str]:
    return [d.nome for d in ementa.disciplinas]


# --- prioridade ---------------------------------------------------------------------------


def test_programacao_vai_na_frente() -> None:
    assert ler_ementa.priorizar([CALCULO, PROGRAMACAO, ETICA]) == (
        [PROGRAMACAO],
        [CALCULO, ETICA],
    )


def test_sem_cara_de_programacao_le_tudo_de_uma_vez() -> None:
    assert ler_ementa.priorizar([CALCULO, ETICA]) == ([CALCULO, ETICA], [])


@pytest.mark.parametrize(
    ("texto", "programacao"),
    [("Java básico", True), ("JavaScript", False), ("C++ moderno", True), ("Física", False)],
)
def test_sinais_de_programacao(texto: str, programacao: bool) -> None:
    assert bool(ler_ementa.priorizar([texto, "x"])[1]) is programacao


# --- duas levas ---------------------------------------------------------------------------


def test_assuntos_ficam_prontos_antes_do_resto_ser_lido(
    db: Session,
    ementa: Ementa,
    sessao_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorPorParte(sessao_factory, ementa.id)

    ler(db, ementa, provedor, [CALCULO, PROGRAMACAO, ETICA], monkeypatch)

    assert provedor.lidas == [PROGRAMACAO, CALCULO, ETICA]
    # Quando Cálculo e Ética eram lidas, a ementa já estava pronta para revisar.
    assert provedor.estados == [("processando", 0), ("prontos", 2), ("prontos", 2)]
    assert (ementa.status_assuntos, ementa.partes_pendentes) == (StatusAssuntos.prontos, 0)
    assert nomes(ementa) == ["Algoritmos", "Cálculo I", "Ética"]
    assert [d.ordem for d in ementa.disciplinas] == [0, 1, 2]


def test_disciplina_partida_entre_levas_ganha_os_assuntos_novos(
    db: Session,
    ementa: Ementa,
    sessao_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorPorParte(sessao_factory, ementa.id)
    provedor.respostas[ETICA] = leitura("Algoritmos", True, "Laços de repetição", "Recursão")

    ler(db, ementa, provedor, [PROGRAMACAO, ETICA], monkeypatch)

    [algoritmos] = ementa.disciplinas
    assert [a.texto for a in algoritmos.assuntos] == [
        "Variáveis e tipos",
        "Laços de repetição",
        "Recursão",
    ]


def test_primeira_leva_sem_programacao_le_o_resto_na_hora(
    db: Session,
    ementa: Ementa,
    sessao_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorPorParte(sessao_factory, ementa.id)
    # Tinha cara de programação, mas o modelo disse que não é.
    provedor.respostas[PROGRAMACAO] = leitura("Banco de Dados", False, "SQL")

    ler(db, ementa, provedor, [PROGRAMACAO, CALCULO], monkeypatch)

    assert provedor.estados == [("processando", 0), ("processando", 0)]
    assert nomes(ementa) == ["Banco de Dados", "Cálculo I"]


def test_segunda_leva_com_a_ia_fora_mantem_a_primeira(
    db: Session,
    ementa: Ementa,
    sessao_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorPorParte(sessao_factory, ementa.id)
    provedor.fora_em = CALCULO

    ler(db, ementa, provedor, [PROGRAMACAO, CALCULO], monkeypatch)

    assert (ementa.status_assuntos, ementa.partes_pendentes) == (StatusAssuntos.prontos, 0)
    assert nomes(ementa) == ["Algoritmos"]


# --- parte inválida -----------------------------------------------------------------------


def test_parte_invalida_e_pulada(
    db: Session,
    ementa: Ementa,
    sessao_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorPorParte(sessao_factory, ementa.id)
    # O modelo que se repete até o teto: JSON cortado no meio.
    provedor.respostas[CALCULO] = '{"disciplinas": [{"nome": "Cálc'

    ler(db, ementa, provedor, [PROGRAMACAO, CALCULO, ETICA], monkeypatch)

    assert ementa.status_assuntos is StatusAssuntos.prontos
    assert nomes(ementa) == ["Algoritmos", "Ética"]


def test_todas_as_partes_invalidas_falham(
    db: Session,
    ementa: Ementa,
    sessao_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorPorParte(sessao_factory, ementa.id)
    provedor.respostas = {parte: "não é JSON" for parte in RESPOSTAS}

    ler(db, ementa, provedor, [CALCULO, ETICA], monkeypatch)

    assert ementa.status_assuntos is StatusAssuntos.falhou
    assert ementa.erro_assuntos == assuntos_ementa.ERRO_SAIDA_INVALIDA


def test_nao_rele_enquanto_a_segunda_leva_roda(db: Session, ementa: Ementa) -> None:
    ementa.status_assuntos = StatusAssuntos.prontos
    ementa.partes_pendentes = 2
    db.commit()

    assert not ementas.reler_assuntos(db, ementa)
