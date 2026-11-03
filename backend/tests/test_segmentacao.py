"""Partes de um vídeo transcrito, para virarem módulos (#209).

O provedor falso devolve a segmentação pronta; o que se confere é o que a skill
e o serviço fazem com ela: o vídeo curto sem IA, o ajuste às fronteiras de fala
e o corte por duração quando a resposta não presta.
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
from app.ia import IAIndisponivel, MensagemIA
from app.ia.eco import Eco
from app.ia.skills import segmentar_video
from app.ia.skills.segmentar_video import Parte
from app.ia.vault import ingerir_video
from app.ia.vault.trechos import Fala, Trecho
from app.models import StatusVideo, VideoYoutube
from app.services import segmentacao
from app.tarefas import segmentacao as tarefa

# Uma aula de uma hora: uma fala por minuto, sobre três assuntos. Cada fala tem
# o tamanho de um trecho do vault (~800 caracteres, o que se fala num minuto), e
# as fronteiras que a segmentação usa são as dos trechos.
FALAS = [
    Fala(
        f"{assunto} {minuto}. " + "Explicação do assunto. " * 30, minuto * 60.0, minuto * 60.0 + 60
    )
    for minuto, assunto in enumerate(
        ["Apresentação"] * 2 + ["Variáveis"] * 18 + ["Condicionais"] * 20 + ["Laços"] * 20
    )
]


class ProvedorDeSegmentacao(Eco):
    def __init__(self, resposta: dict | str) -> None:
        self.resposta = resposta if isinstance(resposta, str) else json.dumps(resposta)
        self.chamadas: list[list[MensagemIA]] = []
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
        self.chamadas.append(list(mensagens))
        yield self.resposta


def video_transcrito(db: Session, duracao: int, falas: list[Fala] = FALAS) -> VideoYoutube:
    video = VideoYoutube(
        youtube_id=f"v{duracao}",
        titulo="Aula de Python",
        duracao_segundos=duracao,
        status=StatusVideo.transcrito,
    )
    db.add(video)
    db.commit()
    asyncio.run(ingerir_video(db, Eco(), video, falas))
    return video


def segmentar(db: Session, provedor, video: VideoYoutube):
    return asyncio.run(segmentacao.segmentar(db, provedor, video))


# --- serviço ------------------------------------------------------------------------------


def test_aula_longa_volta_em_partes_com_os_cortes_nas_falas(db: Session) -> None:
    """O critério da #209: uma hora sobre três assuntos, três partes."""
    video = video_transcrito(db, 3600)
    provedor = ProvedorDeSegmentacao(
        {
            "partes": [
                # O modelo erra os segundos: o ajuste leva cada corte para a
                # fala mais próxima e encosta uma parte na outra.
                {
                    "inicio": 118,
                    "fim": 1190,
                    "titulo": "Variáveis",
                    "resumo": "Tipos e atribuição.",
                },
                {"inicio": 1205, "fim": 2390, "titulo": "Condicionais"},
                {"inicio": 2410, "fim": 3700, "titulo": "Laços"},
            ]
        }
    )

    partes = segmentar(db, provedor, video)

    assert [(p.ordem, p.inicio_segundos, p.fim_segundos, p.titulo) for p in partes] == [
        (0, 120.0, 1200.0, "Variáveis"),
        (1, 1200.0, 2400.0, "Condicionais"),
        (2, 2400.0, 3600.0, "Laços"),
    ]
    assert partes[0].resumo == "Tipos e atribuição."
    # O modelo recebe o índice, não a transcrição inteira.
    pedido = provedor.chamadas[0][1].conteudo
    assert pedido.startswith("Título da aula: Aula de Python")
    assert "[0-" in pedido


def test_aula_curta_volta_inteira_sem_chamar_a_ia(db: Session) -> None:
    video = video_transcrito(db, 15 * 60, FALAS[:15])
    provedor = ProvedorDeSegmentacao({"partes": []})

    [parte] = segmentar(db, provedor, video)

    assert (parte.inicio_segundos, parte.fim_segundos, parte.titulo) == (0, 900, "Aula de Python")
    assert provedor.chamadas == []


def test_resposta_invalida_corta_por_duracao(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "segmentacao_duracao_maxima", 25 * 60)
    video = video_transcrito(db, 3600)

    partes = segmentar(db, ProvedorDeSegmentacao("não sei dividir"), video)

    assert [(p.inicio_segundos, p.fim_segundos) for p in partes] == [
        (0.0, 1500.0),
        (1500.0, 3000.0),
        (3000.0, 3600.0),
    ]
    assert [p.titulo for p in partes] == [
        "Aula de Python (parte 1)",
        "Aula de Python (parte 2)",
        "Aula de Python (parte 3)",
    ]


def test_ia_fora_estoura_para_a_fila_tentar_de_novo(db: Session) -> None:
    video = video_transcrito(db, 3600)
    provedor = ProvedorDeSegmentacao({"partes": []})
    provedor.fora = True

    with pytest.raises(IAIndisponivel):
        segmentar(db, provedor, video)


def test_segmentar_de_novo_substitui_as_partes(db: Session) -> None:
    video = video_transcrito(db, 3600)
    segmentar(db, ProvedorDeSegmentacao("inválida"), video)

    partes = segmentar(
        db, ProvedorDeSegmentacao({"partes": [{"inicio": 0, "fim": 3600, "titulo": "Tudo"}]}), video
    )

    assert [p.titulo for p in partes] == ["Tudo"]
    db.expire_all()
    assert len(db.get(VideoYoutube, video.id).partes) == 1


# --- skill --------------------------------------------------------------------------------


def test_ajuste_descarta_a_introducao_e_junta_partes_no_mesmo_corte() -> None:
    fronteiras = [0, 60, 120, 600, 1200]
    partes = [
        Parte(inicio=130, fim=590, titulo="A"),
        Parte(inicio=125, fim=580, titulo="Repetida"),
        Parte(inicio=610, fim=5000, titulo="B"),
    ]

    ajustadas = segmentar_video.ajustar(partes, fronteiras, duracao=1200)

    # As duas primeiras caem no corte dos 120 s: fica a última delas.
    assert [(p.inicio, p.fim, p.titulo) for p in ajustadas] == [
        (120, 600, "A"),
        (600, 1200, "B"),
    ]


def test_indice_junta_trechos_quando_sao_muitos() -> None:
    trechos = [Trecho(f"trecho {i}", i * 10.0, i * 10.0 + 10) for i in range(150)]

    linhas = segmentar_video.indice(trechos).splitlines()

    assert len(linhas) == 50
    assert linhas[0] == "[0-30] trecho 0 trecho 1 trecho 2"


def test_por_duracao_nunca_corta_no_meio_de_uma_fala() -> None:
    partes = segmentar_video.por_duracao("Aula", [0, 700, 1400, 2100], 2500, maximo_segundos=1500)

    assert [(p.inicio, p.fim) for p in partes] == [(0, 1400), (1400, 2500)]


# --- tarefa e fila ------------------------------------------------------------------------


def test_tarefa_so_segmenta_video_transcrito(
    db: Session, sessao_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tarefa, "SessionLocal", sessao_factory)
    monkeypatch.setattr(tarefa, "get_provedor_ia_tarefas", lambda: ProvedorDeSegmentacao("x"))
    categorizacoes: list[int] = []

    class Espia:
        def categorizacao(self, video_id: int) -> bool:
            categorizacoes.append(video_id)
            return True

    monkeypatch.setattr(tarefa, "fila_das_tarefas", Espia)
    pronto = video_transcrito(db, 600, FALAS[:10])
    aguardando = VideoYoutube(youtube_id="novo", titulo="Novo", duracao_segundos=600)
    db.add(aguardando)
    db.commit()

    tarefa.segmentar(pronto.id)
    tarefa.segmentar(aguardando.id)

    db.expire_all()
    assert len(db.get(VideoYoutube, pronto.id).partes) == 1
    assert db.get(VideoYoutube, aguardando.id).partes == []
    # O vídeo segmentado vai para a categorização (#202).
    assert categorizacoes == [pronto.id]


def test_segmentacao_entra_na_fila_uma_vez_por_video() -> None:
    fila = FilaRedis(fakeredis.FakeRedis(), "teste")

    assert fila.segmentacao(4) is True
    assert fila.segmentacao(4) is False

    assert fila.fila.job_ids == ["segmentacao-4"]
