"""Seed das trilhas extras: grava as três, e rodar de novo não duplica nada."""

import json
import textwrap

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Atividade, CasoDeTeste, Modulo, Trilha
from app.models.enums import TipoAtividade
from app.sandbox import executar
from app.seeds import trilhas_extras
from app.services.desafios import normalizar_saida
from app.services.submissoes import corrigir

# Uma solução de referência por desafio: prova que os casos do seed têm solução
# e que a saída esperada está escrita do jeito que o corretor compara.
SOLUCOES = {
    "logica-de-programacao": textwrap.dedent(
        """
        n = int(input())
        for i in range(n, 0, -1):
            print(i)
        print("Fim!")
        """
    ),
    "estruturas-de-dados": textwrap.dedent(
        """
        lista = [int(x) for x in input().split()]
        alvo = int(input())
        ini, fim, posicao = 0, len(lista) - 1, -1
        while ini <= fim:
            meio = (ini + fim) // 2
            if lista[meio] == alvo:
                posicao = meio
                break
            if lista[meio] < alvo:
                ini = meio + 1
            else:
                fim = meio - 1
        print(posicao)
        """
    ),
    "banco-de-dados-sql": textwrap.dedent(
        """
        import sqlite3
        import sys

        banco = sqlite3.connect(":memory:")
        banco.execute("CREATE TABLE alunos (nome TEXT, nota REAL)")
        for linha in sys.stdin:
            if not linha.strip():
                break
            nome, nota = linha.split()
            banco.execute("INSERT INTO alunos VALUES (?, ?)", (nome, float(nota)))
        consulta = "SELECT nome FROM alunos WHERE nota >= 7 ORDER BY nota DESC"
        for (nome,) in banco.execute(consulta):
            print(nome)
        """
    ),
}


def test_grava_as_tres_trilhas_publicadas_com_4_modulos_e_o_desafio(db: Session) -> None:
    trilhas = trilhas_extras.aplicar(db)

    assert [t.slug for t in trilhas] == [
        "logica-de-programacao",
        "estruturas-de-dados",
        "banco-de-dados-sql",
    ]
    for trilha in trilhas:
        db.refresh(trilha)
        assert trilha.publicada
        assert [m.ordem for m in trilha.modulos] == [1, 2, 3, 4]
        assert all(len(m.atividades) == 5 for m in trilha.modulos[:-1])
        # O último módulo traz o desafio proposto (#25), com casos de teste.
        ultimo = trilha.modulos[-1].atividades
        assert len(ultimo) == 6
        assert ultimo[-1].tipo is TipoAtividade.desafio_codigo


def test_rodar_de_novo_nao_duplica(db: Session) -> None:
    trilhas_extras.aplicar(db)
    contagem = (
        db.scalar(select(func.count(Trilha.id))),
        db.scalar(select(func.count(Modulo.id))),
        db.scalar(select(func.count(Atividade.id))),
    )

    trilhas_extras.aplicar(db)

    assert contagem == (
        db.scalar(select(func.count(Trilha.id))),
        db.scalar(select(func.count(Modulo.id))),
        db.scalar(select(func.count(Atividade.id))),
    )


def test_o_gabarito_de_cada_atividade_corrigivel_e_aceito_pela_correcao(db: Session) -> None:
    """O gabarito do seed é a resposta certa para o corretor do app, não só no papel."""
    trilhas_extras.aplicar(db)
    for atividade in db.scalars(select(Atividade)):
        if atividade.tipo in (TipoAtividade.resposta_aberta, TipoAtividade.desafio_codigo):
            continue
        assert corrigir(atividade, atividade.resposta_esperada).correta, atividade.enunciado
        if atividade.tipo is TipoAtividade.ordenacao:
            # E a ordem em que a tela mostra as linhas não é a certa.
            embaralhada = json.dumps(atividade.opcoes, ensure_ascii=False)
            assert not corrigir(atividade, embaralhada).correta, atividade.enunciado


def test_cada_desafio_tem_solucao_que_passa_nos_casos(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "sandbox_modo", "processo")
    for trilha in trilhas_extras.aplicar(db):
        db.refresh(trilha)
        desafio = next(
            a
            for m in trilha.modulos
            for a in m.atividades
            if a.tipo is TipoAtividade.desafio_codigo
        )
        casos = list(db.scalars(select(CasoDeTeste).where(CasoDeTeste.atividade_id == desafio.id)))
        assert len(casos) == 3 and casos[0].publico and not casos[1].publico
        for caso in casos:
            resultado = executar(SOLUCOES[trilha.slug], caso.entrada)
            assert resultado.codigo_saida == 0, resultado.stderr
            assert normalizar_saida(resultado.stdout) == normalizar_saida(caso.saida_esperada)
