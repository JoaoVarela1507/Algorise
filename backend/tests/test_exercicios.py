"""Exercícios de prática gerados a partir do conteúdo do módulo (#201).

O provedor falso responde a lista pronta e guarda o pedido, para conferir que o
prompt leva só o conteúdo daquele módulo (no módulo de vídeo, só o intervalo).
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Sequence
from typing import Any

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.fila import FilaRedis
from app.ia import IAIndisponivel, MensagemIA, get_provedor_ia_tarefas
from app.ia.eco import Eco
from app.ia.skills import exercicios as skill
from app.ia.vault import ingerir_transcricao, ingerir_video
from app.ia.vault.trechos import Fala
from app.main import app
from app.models import (
    ExerciciosGerados,
    Modulo,
    NivelExperiencia,
    OrigemModulo,
    ParteVideo,
    StatusGeracao,
    Trilha,
    VideoYoutube,
)
from app.services import exercicios

LISTA = {
    "exercicios": [
        {
            "enunciado": "Escreva um laço que imprime de 1 a 5.",
            "resposta_esperada": "for i in range(1, 6):\n    print(i)",
            "dica": "Use range.",
        }
    ]
}


class ProvedorDeExercicios(Eco):
    def __init__(self, resposta: dict | str = LISTA) -> None:
        self.resposta = resposta if isinstance(resposta, str) else json.dumps(resposta)
        self.pedidos: list[list[MensagemIA]] = []
        self.fora = False

    async def gerar(
        self,
        mensagens: Sequence[MensagemIA],
        *,
        max_tokens: int,
        formato: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str]:
        if self.fora:
            raise IAIndisponivel("fora (simulado no teste)")
        self.pedidos.append(list(mensagens))
        yield self.resposta


@pytest.fixture
def lacos(db: Session) -> Modulo:
    """Módulo do catálogo, com a transcrição do vídeo dele no vault."""
    trilha = Trilha(slug="python", nome="Python", disciplina="Algoritmos", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Laços", descricao="for e while")]
    db.add(trilha)
    db.commit()
    asyncio.run(
        ingerir_transcricao(
            db,
            Eco(),
            modulo_id=trilha.modulos[0].id,
            conteudo="O laço for percorre uma lista.",
            nome_arquivo="aula.txt",
        )
    )
    return trilha.modulos[0]


def gerar(db: Session, provedor, modulo: Modulo, nivel=NivelExperiencia.baixo) -> ExerciciosGerados:
    geracao, _ = exercicios.pedir(db, modulo, nivel)
    asyncio.run(exercicios.gerar(db, provedor, geracao))
    return geracao


# --- serviço ------------------------------------------------------------------------------


def test_modulo_com_transcricao_ganha_exercicios_no_formato_validado(
    db: Session, lacos: Modulo
) -> None:
    """O critério da #201."""
    provedor = ProvedorDeExercicios()

    geracao = gerar(db, provedor, lacos)

    assert geracao.status is StatusGeracao.pronto
    assert geracao.exercicios == LISTA["exercicios"]
    pedido = provedor.pedidos[0][1].conteudo
    assert "Módulo: Laços" in pedido
    assert "O laço for percorre uma lista." in pedido
    assert "começando a programar" in pedido


def test_sem_conteudo_no_vault_nao_gera(db: Session) -> None:
    trilha = Trilha(slug="vazia", nome="Vazia", disciplina="X", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Sem vídeo")]
    db.add(trilha)
    db.commit()
    provedor = ProvedorDeExercicios()

    geracao = gerar(db, provedor, trilha.modulos[0])

    assert (geracao.status, geracao.exercicios, provedor.pedidos) == (
        StatusGeracao.sem_conteudo,
        [],
        [],
    )


def test_modulo_de_video_usa_so_o_trecho_do_intervalo(db: Session) -> None:
    video = VideoYoutube(youtube_id="v1", titulo="Aula", duracao_segundos=1200)
    video.partes = [ParteVideo(ordem=1, inicio_segundos=600, fim_segundos=1200, titulo="Funções")]
    db.add(video)
    db.commit()
    falas = [
        Fala("Laços repetem um bloco. " * 33, 0, 600),
        Fala("Funções recebem parâmetros. " * 28, 600, 1200),
    ]
    asyncio.run(ingerir_video(db, Eco(), video, falas))
    trilha = Trilha(slug="t", nome="T", disciplina="Algoritmos", publicada=True)
    trilha.modulos = [
        Modulo(
            ordem=1,
            titulo="Funções",
            origem=OrigemModulo.youtube,
            inicio_segundos=600,
            fim_segundos=1200,
            parte_video=video.partes[0],
        )
    ]
    db.add(trilha)
    db.commit()

    conteudo = " ".join(exercicios.conteudo_do_modulo(db, trilha.modulos[0]))

    assert "Funções recebem parâmetros" in conteudo
    # O trecho de laços (até os 600 s) fica de fora; sobra só a sobreposição
    # que o trecho seguinte repete, poucas frases.
    assert conteudo.count("Laços repetem") < 10


def test_saida_invalida_falha_e_e_refeita_no_proximo_pedido(db: Session, lacos: Modulo) -> None:
    geracao = gerar(db, ProvedorDeExercicios("não sei"), lacos)
    assert (geracao.status, geracao.erro) == (StatusGeracao.falhou, exercicios.ERRO_SAIDA_INVALIDA)

    de_novo, enfileirar = exercicios.pedir(db, lacos, NivelExperiencia.baixo)

    assert (de_novo.id, de_novo.status, enfileirar) == (geracao.id, StatusGeracao.gerando, True)


def test_ia_fora_estoura_para_a_fila_tentar_de_novo(db: Session, lacos: Modulo) -> None:
    provedor = ProvedorDeExercicios()
    provedor.fora = True
    geracao, _ = exercicios.pedir(db, lacos, NivelExperiencia.baixo)

    with pytest.raises(IAIndisponivel):
        asyncio.run(exercicios.gerar(db, provedor, geracao))

    assert geracao.status is StatusGeracao.falhou


def test_uma_geracao_por_modulo_e_nivel(db: Session, lacos: Modulo) -> None:
    baixo = gerar(db, ProvedorDeExercicios(), lacos)

    mesmo, enfileirar = exercicios.pedir(db, lacos, NivelExperiencia.baixo)
    alto, enfileirar_alto = exercicios.pedir(db, lacos, NivelExperiencia.alto)

    assert (mesmo.id, enfileirar) == (baixo.id, False)
    assert (alto.id != baixo.id, enfileirar_alto) == (True, True)


def test_skill_recusa_lista_vazia() -> None:
    with pytest.raises(skill.SaidaInvalida):
        skill.ler_resposta('{"exercicios": []}')


# --- rota e fila --------------------------------------------------------------------------


def test_rota_gera_na_primeira_vez_e_serve_depois(
    cliente: TestClient, autenticado: dict[str, str], lacos: Modulo
) -> None:
    provedor = ProvedorDeExercicios()
    app.dependency_overrides[get_provedor_ia_tarefas] = lambda: provedor

    primeira = cliente.get("/api/v1/trilhas/python/passos/1/exercicios", headers=autenticado)
    segunda = cliente.get("/api/v1/trilhas/python/passos/1/exercicios", headers=autenticado)

    # A primeira resposta sai antes da geração, que roda depois dela.
    assert (primeira.status_code, primeira.json()) == (200, {"status": "gerando", "exercicios": []})
    assert segunda.json() == {"status": "pronto", "exercicios": LISTA["exercicios"]}
    assert len(provedor.pedidos) == 1


def test_rota_respeita_o_passo_bloqueado(
    cliente: TestClient, autenticado: dict[str, str], lacos: Modulo, db: Session
) -> None:
    db.add(Modulo(trilha_id=lacos.trilha_id, ordem=2, titulo="Funções"))
    db.commit()

    resposta = cliente.get("/api/v1/trilhas/python/passos/2/exercicios", headers=autenticado)

    assert resposta.status_code == 403


def test_exercicios_entram_na_fila_uma_vez_por_geracao() -> None:
    fila = FilaRedis(fakeredis.FakeRedis(), "teste")

    assert fila.exercicios(8) is True
    assert fila.exercicios(8) is False

    assert fila.fila.job_ids == ["exercicios-8"]
