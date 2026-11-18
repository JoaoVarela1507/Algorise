"""Seed das trilhas novas: grava as cinco, e rodar de novo não duplica nada."""

import json
import textwrap

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Atividade, CasoDeTeste, Modulo, Trilha
from app.models.enums import TipoAtividade
from app.sandbox import executar
from app.seeds import trilhas_novas
from app.services.desafios import normalizar_saida
from app.services.submissoes import corrigir

# Uma solução de referência por desafio: prova que os casos do seed têm solução
# e que a saída esperada está escrita do jeito que o corretor compara.
SOLUCOES = {
    "git-e-controle-de-versao": textwrap.dedent(
        """
        n = int(input())
        total = {}
        for _ in range(n):
            _hash, autor, _mensagem = input().split(maxsplit=2)
            total[autor] = total.get(autor, 0) + 1
        for autor, quantidade in sorted(total.items(), key=lambda item: (-item[1], item[0])):
            print(f"{autor}: {quantidade}")
        """
    ),
    "programacao-orientada-a-objetos": textwrap.dedent(
        """
        class Conta:
            def __init__(self):
                self.saldo = 0

            def depositar(self, valor):
                self.saldo += valor

            def sacar(self, valor):
                if valor > self.saldo:
                    print("Saldo insuficiente")
                else:
                    self.saldo -= valor


        conta = Conta()
        for _ in range(int(input())):
            operacao, valor = input().split()
            if operacao == "depositar":
                conta.depositar(int(valor))
            else:
                conta.sacar(int(valor))
        print(f"Saldo: {conta.saldo}")
        """
    ),
    "matematica-discreta": textwrap.dedent(
        """
        a, b = map(int, input().split())
        x, y = a, b
        while y:
            x, y = y, x % y
        print(f"MDC: {x}")
        print(f"MMC: {a * b // x}")
        """
    ),
    "redes-de-computadores": textwrap.dedent(
        """
        partes = input().strip().split(".")
        valido = len(partes) == 4 and all(
            p.isdigit() and 0 <= int(p) <= 255 for p in partes
        )
        if not valido:
            print("Invalido")
        else:
            primeiro = int(partes[0])
            if primeiro <= 127:
                classe = "A"
            elif primeiro <= 191:
                classe = "B"
            elif primeiro <= 223:
                classe = "C"
            elif primeiro <= 239:
                classe = "D"
            else:
                classe = "E"
            print(f"Classe {classe}")
        """
    ),
    "ordenacao-e-complexidade": textwrap.dedent(
        """
        v = [int(x) for x in input().split()]
        trocas = 0
        for i in range(len(v)):
            for j in range(len(v) - 1 - i):
                if v[j] > v[j + 1]:
                    v[j], v[j + 1] = v[j + 1], v[j]
                    trocas += 1
        print(" ".join(str(x) for x in v))
        print(f"Trocas: {trocas}")
        """
    ),
}


def test_grava_as_cinco_trilhas_publicadas_com_4_modulos_e_o_desafio(db: Session) -> None:
    trilhas = trilhas_novas.aplicar(db)

    assert [t.slug for t in trilhas] == [
        "git-e-controle-de-versao",
        "programacao-orientada-a-objetos",
        "matematica-discreta",
        "redes-de-computadores",
        "ordenacao-e-complexidade",
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
    trilhas_novas.aplicar(db)
    contagem = (
        db.scalar(select(func.count(Trilha.id))),
        db.scalar(select(func.count(Modulo.id))),
        db.scalar(select(func.count(Atividade.id))),
    )

    trilhas_novas.aplicar(db)

    assert contagem == (
        db.scalar(select(func.count(Trilha.id))),
        db.scalar(select(func.count(Modulo.id))),
        db.scalar(select(func.count(Atividade.id))),
    )


def test_o_gabarito_de_cada_atividade_corrigivel_e_aceito_pela_correcao(db: Session) -> None:
    """O gabarito do seed é a resposta certa para o corretor do app, não só no papel."""
    trilhas_novas.aplicar(db)
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
    for trilha in trilhas_novas.aplicar(db):
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
