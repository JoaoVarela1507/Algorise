"""Matéria de cada parte de vídeo e as lacunas que ela cobre (#202).

O provedor falso responde uma classificação por parte, na ordem; o que se
confere é o que o serviço faz com ela: a matéria só da lista, o limite de
confiança, e a lacuna que nenhuma parte cobriu voltando para a busca.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Sequence
from typing import Any

import fakeredis
import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.fila import FilaRedis
from app.ia import MensagemIA
from app.ia.eco import Eco
from app.ia.skills import categorizar_videos
from app.ia.vault import ingerir_video
from app.ia.vault.trechos import Fala
from app.models import (
    Lacuna,
    ParteVideo,
    StatusLacuna,
    StatusVideo,
    Trilha,
    VideoLacuna,
    VideoYoutube,
)
from app.services import busca_conteudo, categorizacao
from app.tarefas import categorizacao as tarefa


class ProvedorDeCategorias(Eco):
    def __init__(self, *respostas: dict | str) -> None:
        self.respostas = [r if isinstance(r, str) else json.dumps(r) for r in respostas]
        self.pedidos: list[list[MensagemIA]] = []

    async def gerar(
        self,
        mensagens: Sequence[MensagemIA],
        *,
        max_tokens: int,
        formato: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str]:
        self.pedidos.append(list(mensagens))
        yield self.respostas[len(self.pedidos) - 1]


def resposta(materia: str, assuntos: list[int], confianca: float = 0.9) -> dict:
    return {
        "materia": materia,
        "assuntos": assuntos,
        "confianca": confianca,
        "justificativa": "...",
    }


@pytest.fixture
def cenario(db: Session) -> tuple[VideoYoutube, Lacuna, Lacuna]:
    """Um vídeo de duas partes, ligado a duas lacunas de Algoritmos, e uma trilha de SQL."""
    db.add(Trilha(slug="sql", nome="SQL", disciplina="Banco de Dados", periodo=3))
    lacos = Lacuna(chave="algoritmos|lacos", disciplina="Algoritmos", assunto="Laços")
    recursao = Lacuna(chave="algoritmos|recursao", disciplina="Algoritmos", assunto="Recursão")
    for lacuna in (lacos, recursao):
        lacuna.status = StatusLacuna.em_preparacao
    video = VideoYoutube(
        youtube_id="v1", titulo="Aula", duracao_segundos=1200, status=StatusVideo.transcrito
    )
    video.lacunas = [
        VideoLacuna(lacuna=lacos, distancia=0.2),
        VideoLacuna(lacuna=recursao, distancia=0.3),
    ]
    video.partes = [
        ParteVideo(ordem=0, inicio_segundos=0, fim_segundos=600, titulo="Laços"),
        ParteVideo(ordem=1, inicio_segundos=600, fim_segundos=1200, titulo="Apresentação do canal"),
    ]
    db.add(video)
    db.commit()
    # Cada fala enche um trecho do vault (~800 caracteres).
    falas = [
        Fala("O laço for repete um bloco. " * 28, 0, 600),
        Fala("Inscreva-se no canal e ative o sininho. " * 19, 600, 1200),
    ]
    asyncio.run(ingerir_video(db, Eco(), video, falas))
    return video, lacos, recursao


def categorizar(db: Session, provedor, video: VideoYoutube) -> set[str]:
    return asyncio.run(categorizacao.categorizar(db, provedor, video))


def test_parte_da_disciplina_e_aprovada_com_a_lacuna_certa(db: Session, cenario) -> None:
    """O critério da #202."""
    video, lacos, _ = cenario
    provedor = ProvedorDeCategorias(resposta("ALGORITMOS", [1]), resposta("nenhuma", []))

    categorizar(db, provedor, video)

    aula, propaganda = video.partes
    assert (aula.disciplina, aula.aprovada, [lacuna.id for lacuna in aula.lacunas]) == (
        "Algoritmos",
        True,
        [lacos.id],
    )
    assert (propaganda.disciplina, propaganda.aprovada, propaganda.lacunas) == (None, False, [])
    # A transcrição de cada parte é só a do intervalo dela.
    assert "laço for" in provedor.pedidos[0][1].conteudo
    assert "sininho" not in provedor.pedidos[0][1].conteudo


def test_materia_inventada_vira_nenhuma(db: Session, cenario) -> None:
    video, _, _ = cenario
    provedor = ProvedorDeCategorias(resposta("Culinária", [1]), resposta("nenhuma", []))

    categorizar(db, provedor, video)

    assert (video.partes[0].disciplina, video.partes[0].aprovada) == (None, False)


def test_confianca_baixa_descarta_a_parte(
    db: Session, cenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "categorizacao_confianca_minima", 0.6)
    video, _, _ = cenario
    provedor = ProvedorDeCategorias(resposta("Algoritmos", [1], 0.4), resposta("nenhuma", []))

    categorizar(db, provedor, video)

    assert (video.partes[0].disciplina, video.partes[0].aprovada) == ("Algoritmos", False)


def test_lacuna_que_nenhuma_parte_cobre_volta_para_a_busca(db: Session, cenario) -> None:
    video, lacos, recursao = cenario
    provedor = ProvedorDeCategorias(resposta("Algoritmos", [1]), resposta("nenhuma", []))

    de_volta = categorizar(db, provedor, video)

    assert de_volta == {"Algoritmos"}
    assert (lacos.status, recursao.status) == (StatusLacuna.em_preparacao, StatusLacuna.pendente)
    recusadas = {ligacao.lacuna_id: ligacao.recusada for ligacao in video.lacunas}
    assert recusadas == {lacos.id: False, recursao.id: True}


def test_lacuna_com_outro_video_a_caminho_continua_em_preparacao(db: Session, cenario) -> None:
    video, _, recursao = cenario
    outro = VideoYoutube(youtube_id="v2", titulo="Recursão")
    outro.lacunas = [VideoLacuna(lacuna=recursao, distancia=0.1)]
    db.add(outro)
    db.commit()
    provedor = ProvedorDeCategorias(resposta("Algoritmos", [1]), resposta("nenhuma", []))

    assert categorizar(db, provedor, video) == set()
    assert recursao.status is StatusLacuna.em_preparacao


def test_resposta_invalida_descarta_a_parte_sem_derrubar_o_resto(db: Session, cenario) -> None:
    video, _, _ = cenario
    provedor = ProvedorDeCategorias("não sei", resposta("Banco de Dados", []))

    categorizar(db, provedor, video)

    assert video.partes[0].aprovada is False
    assert video.partes[0].justificativa == categorizacao.JUSTIFICATIVA_INVALIDA
    assert (video.partes[1].disciplina, video.partes[1].aprovada) == ("Banco de Dados", True)


def test_materias_sao_as_das_trilhas_e_das_lacunas(db: Session, cenario) -> None:
    _video, lacos, recursao = cenario

    assert categorizacao.materias_possiveis(db, [lacos, recursao]) == [
        "Algoritmos",
        "Banco de Dados",
    ]


def test_busca_nao_escolhe_de_novo_o_video_recusado(db: Session, cenario) -> None:
    video, _, recursao = cenario
    categorizar(
        db, ProvedorDeCategorias(resposta("Algoritmos", [1]), resposta("nenhuma", [])), video
    )

    assert busca_conteudo._recusados(db, [recursao.id]) == {recursao.id: {"v1"}}


def test_skill_numera_os_assuntos_a_partir_de_um() -> None:
    categoria = categorizar_videos.ler_resposta(
        json.dumps(resposta("algoritmos", [2, 7, 0])), ["Algoritmos"], total_de_assuntos=3
    )

    assert (categoria.materia, categoria.assuntos) == ("Algoritmos", [1])


def test_tarefa_categoriza_e_devolve_as_lacunas_para_a_busca(
    db: Session, cenario, sessao_factory, redis_falso, monkeypatch: pytest.MonkeyPatch
) -> None:
    video, _, _ = cenario
    buscas: list[str] = []

    class Espia:
        def busca_de_conteudo(self, disciplina: str) -> bool:
            buscas.append(disciplina)
            return True

    monkeypatch.setattr(tarefa, "SessionLocal", sessao_factory)
    monkeypatch.setattr(
        tarefa,
        "get_provedor_ia_tarefas",
        lambda: ProvedorDeCategorias(resposta("Algoritmos", [1]), resposta("nenhuma", [])),
    )
    monkeypatch.setattr(tarefa, "fila_das_tarefas", Espia)

    tarefa.categorizar(video.id)

    assert buscas == ["Algoritmos"]


def test_categorizacao_entra_na_fila_uma_vez_por_video() -> None:
    fila = FilaRedis(fakeredis.FakeRedis(), "teste")

    assert fila.categorizacao(3) is True
    assert fila.categorizacao(3) is False

    assert fila.fila.job_ids == ["categorizacao-3"]
