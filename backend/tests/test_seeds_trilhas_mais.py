"""Seed das trilhas novas: grava as quatro, e rodar de novo não duplica nada."""

import json
import textwrap

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Atividade, CasoDeTeste, Modulo, Trilha
from app.models.enums import TipoAtividade
from app.sandbox import executar
from app.seeds import trilhas_mais
from app.services.desafios import normalizar_saida
from app.services.submissoes import corrigir

# Uma solução de referência por desafio: prova que os casos do seed têm solução
# e que a saída esperada está escrita do jeito que o corretor compara.
SOLUCOES = {
    "sistemas-operacionais": textwrap.dedent(
        """
        n = int(input())
        tempos = [int(x) for x in input().split()]
        espera = 0
        acumulado = 0
        for t in tempos:
            espera += acumulado
            acumulado += t
        print(f"Espera media: {espera / n:.2f}")
        """
    ),
    "engenharia-de-software": textwrap.dedent(
        """
        import math

        backlog = int(input())
        pontos = [int(x) for x in input().split()]
        media = sum(pontos) / len(pontos)
        print(f"Velocidade: {media:.1f}")
        print(f"Sprints restantes: {math.ceil(backlog / media)}")
        """
    ),
    "desenvolvimento-web-html-css-http": textwrap.dedent(
        """
        for _ in range(int(input())):
            codigo = int(input())
            if 200 <= codigo <= 299:
                classe = "Sucesso"
            elif 300 <= codigo <= 399:
                classe = "Redirecionamento"
            elif 400 <= codigo <= 499:
                classe = "Erro do cliente"
            elif 500 <= codigo <= 599:
                classe = "Erro do servidor"
            else:
                classe = "Invalido"
            print(f"{codigo} {classe}")
        """
    ),
    "recursao-e-programacao-funcional-em-python": textwrap.dedent(
        """
        def fatorial(n):
            return 1 if n == 0 else n * fatorial(n - 1)


        def fib(n):
            return n if n < 2 else fib(n - 1) + fib(n - 2)


        n = int(input())
        print(f"Fatorial: {fatorial(n)}")
        print(f"Fibonacci: {fib(n)}")
        """
    ),
}


def test_grava_as_quatro_trilhas_publicadas_com_4_modulos_e_o_desafio(db: Session) -> None:
    trilhas = trilhas_mais.aplicar(db)

    assert [t.slug for t in trilhas] == [
        "sistemas-operacionais",
        "engenharia-de-software",
        "desenvolvimento-web-html-css-http",
        "recursao-e-programacao-funcional-em-python",
    ]
    for trilha in trilhas:
        db.refresh(trilha)
        assert trilha.publicada
        assert [m.ordem for m in trilha.modulos] == [1, 2, 3, 4]
        assert all(len(m.atividades) == 5 for m in trilha.modulos[:-1])
        # O último módulo traz o desafio proposto, com casos de teste.
        ultimo = trilha.modulos[-1].atividades
        assert len(ultimo) == 6
        assert ultimo[-1].tipo is TipoAtividade.desafio_codigo


def test_rodar_de_novo_nao_duplica(db: Session) -> None:
    trilhas_mais.aplicar(db)
    contagem = (
        db.scalar(select(func.count(Trilha.id))),
        db.scalar(select(func.count(Modulo.id))),
        db.scalar(select(func.count(Atividade.id))),
    )

    trilhas_mais.aplicar(db)

    assert contagem == (
        db.scalar(select(func.count(Trilha.id))),
        db.scalar(select(func.count(Modulo.id))),
        db.scalar(select(func.count(Atividade.id))),
    )


def test_o_gabarito_de_cada_atividade_corrigivel_e_aceito_pela_correcao(db: Session) -> None:
    """O gabarito do seed é a resposta certa para o corretor do app, não só no papel."""
    trilhas_mais.aplicar(db)
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
    for trilha in trilhas_mais.aplicar(db):
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
