"""Busca de vídeos no YouTube para as lacunas das ementas (#207).

A API é simulada (`MockTransport`), e o embedding é o por tema de
`test_ementa_assuntos`: título e assunto do mesmo tema ficam à distância 0, e o
resto, a 1. Assim o teste diz qual aula cobre qual lacuna sem modelo nenhum.
"""

import asyncio
import json
from collections.abc import Callable, Iterator

import fakeredis
import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.fila import FilaRedis
from app.models import BuscaYoutube, Lacuna, StatusLacuna, StatusVideo, VideoYoutube
from app.services import assuntos_ementa, busca_conteudo
from app.services.youtube import ClienteYoutube, CotaEsgotada, duracao_em_segundos
from app.tarefas import busca as tarefa_busca
from tests.test_ementa_assuntos import ProvedorDeEmenta

DISCIPLINA = "Algoritmos"

PLAYLISTS = [
    {"id": {"playlistId": "PL-recursao"}, "snippet": {"title": "Recursão", "channelTitle": "B"}},
    {"id": {"playlistId": "PL-curso"}, "snippet": {"title": "Curso", "channelTitle": "Prof. A"}},
]
AULAS = {
    # Cobre só a recursão.
    "PL-recursao": [("r1", "Recursão na prática")],
    # Cobre variáveis e repetição: é a escolhida, mesmo vindo depois.
    "PL-curso": [
        ("a0", "Boas-vindas ao curso"),
        ("a1", "Variáveis e tipos"),
        ("a2", "Laços de repetição"),
        ("a3", "Private video"),
    ],
}
AVULSOS = {
    f"{DISCIPLINA} Recursão": [
        ("v-curto", "Recursão em 1 minuto"),
        ("v-rec", "Recursão em Python"),
    ],
    f"{DISCIPLINA} Ponteiros": [("v-pont", "Aula 12")],
}
DURACOES = {
    "r1": "PT8M",
    "a1": "PT12M",
    "a2": "PT15M30S",
    "v-curto": "PT59S",
    "v-rec": "PT20M",
    "v-pont": "PT10M",
}


class ApiFalsa:
    """A YouTube Data API, respondendo do que está acima e contando as chamadas."""

    def __init__(self) -> None:
        self.chamadas: list[httpx2.Request] = []
        self.responder: Callable[[httpx2.Request], httpx2.Response] | None = None

    def __call__(self, pedido: httpx2.Request) -> httpx2.Response:
        self.chamadas.append(pedido)
        if self.responder is not None:
            return self.responder(pedido)
        p = pedido.url.params
        if pedido.url.path.endswith("/search") and p["type"] == "playlist":
            return self._json({"items": PLAYLISTS})
        if pedido.url.path.endswith("/search"):
            itens = [
                {"id": {"videoId": i}, "snippet": {"title": t, "channelTitle": "C"}}
                for i, t in AVULSOS.get(p["q"], [])
            ]
            return self._json({"items": itens})
        if pedido.url.path.endswith("/playlistItems"):
            itens = [
                {"snippet": {"title": t, "position": n, "resourceId": {"videoId": i}}}
                for n, (i, t) in enumerate(AULAS[p["playlistId"]])
            ]
            # O vídeo privado vem sem id, como na API de verdade.
            itens = [
                i
                if i["snippet"]["title"] != "Private video"
                else {"snippet": {"title": "Private video"}}
                for i in itens
            ]
            return self._json({"items": itens})
        if pedido.url.path.endswith("/videos"):
            ids = p["id"].split(",")
            return self._json(
                {
                    "items": [
                        {"id": i, "contentDetails": {"duration": DURACOES[i]}}
                        for i in ids
                        if i in DURACOES
                    ]
                }
            )
        return httpx2.Response(404)

    @staticmethod
    def _json(dados: dict) -> httpx2.Response:
        return httpx2.Response(200, content=json.dumps(dados).encode())

    def recursos(self) -> list[str]:
        return [c.url.path.rsplit("/", 1)[-1] for c in self.chamadas]


@pytest.fixture
def api() -> ApiFalsa:
    return ApiFalsa()


@pytest.fixture
def cliente_yt(db: Session, api: ApiFalsa, redis_falso: fakeredis.FakeRedis) -> ClienteYoutube:
    return ClienteYoutube(db, "chave-de-teste", transport=httpx2.MockTransport(api))


def lacunas(db: Session, *assuntos: str, disciplina: str = DISCIPLINA) -> list[Lacuna]:
    criadas = [
        Lacuna(chave=f"{disciplina}|{assunto}".lower(), disciplina=disciplina, assunto=assunto)
        for assunto in assuntos
    ]
    db.add_all(criadas)
    db.commit()
    return criadas


def buscar(db: Session, cliente_yt: ClienteYoutube, disciplina: str = DISCIPLINA):
    return asyncio.run(busca_conteudo.buscar(db, cliente_yt, ProvedorDeEmenta(), disciplina))


# --- critério de aceite -------------------------------------------------------------------


def test_playlist_que_cobre_mais_lacunas_e_avulsos_para_o_resto(
    db: Session, cliente_yt: ClienteYoutube
) -> None:
    """O critério da #207."""
    repeticao, variaveis, recursao, ponteiros = lacunas(
        db, "Laços de repetição", "Variáveis", "Recursão", "Ponteiros"
    )

    resultado = buscar(db, cliente_yt)

    assert (resultado.playlist_id, resultado.cobertas, resultado.sem_conteudo) == ("PL-curso", 3, 1)
    videos = {v.youtube_id: v for v in db.scalars(select(VideoYoutube))}
    assert set(videos) == {"a1", "a2", "v-rec"}
    # A aula guarda a playlist e a posição; o avulso, não.
    assert (videos["a2"].playlist_id, videos["a2"].posicao, videos["a2"].duracao_segundos) == (
        "PL-curso",
        3,
        930,
    )
    assert (videos["v-rec"].playlist_id, videos["v-rec"].duracao_segundos) == (None, 1200)
    assert {v.status for v in videos.values()} == {StatusVideo.aguardando}
    assert [ligacao.lacuna_id for ligacao in videos["a2"].lacunas] == [repeticao.id]

    db.expire_all()
    estados = {lacuna.assunto: lacuna.status for lacuna in db.scalars(select(Lacuna))}
    assert estados == {
        "Laços de repetição": StatusLacuna.em_preparacao,
        "Variáveis": StatusLacuna.em_preparacao,
        "Recursão": StatusLacuna.em_preparacao,
        "Ponteiros": StatusLacuna.sem_conteudo,
    }
    assert variaveis.id != recursao.id != ponteiros.id


def test_compara_os_titulos_antes_de_qualquer_outra_chamada(
    db: Session, cliente_yt: ClienteYoutube, api: ApiFalsa
) -> None:
    """Duração só se pede para o que casou; a busca avulsa, só para o que sobrou."""
    lacunas(db, "Laços de repetição", "Variáveis", "Recursão", "Ponteiros")

    buscar(db, cliente_yt)

    assert api.recursos() == [
        "search",  # as playlists
        "playlistItems",
        "playlistItems",
        "videos",  # duração das duas aulas que casaram
        "search",  # recursão, avulsa
        "videos",
        "search",  # ponteiros, avulsa
        "videos",
    ]


def test_sem_lacuna_pendente_nao_chama_a_api(
    db: Session, cliente_yt: ClienteYoutube, api: ApiFalsa
) -> None:
    lacunas(db, "Recursão", disciplina="Banco de Dados")

    resultado = buscar(db, cliente_yt)

    assert (resultado.cobertas, api.chamadas) == (0, [])


def test_disciplina_casa_sem_contar_acento_e_caixa(db: Session, cliente_yt: ClienteYoutube) -> None:
    lacunas(db, "Recursão", disciplina="Introdução à Programação")

    assert busca_conteudo.pendentes(db, "INTRODUCAO A PROGRAMACAO")[0].assunto == "Recursão"


def test_aula_longa_demais_na_playlist_vai_buscar_um_avulso(
    db: Session, cliente_yt: ClienteYoutube, monkeypatch: pytest.MonkeyPatch
) -> None:
    lacunas(db, "Variáveis")
    monkeypatch.setitem(DURACOES, "a1", "PT5H")

    resultado = buscar(db, cliente_yt)

    # Sem avulso para variáveis, a lacuna fica sem conteúdo.
    assert (resultado.cobertas, resultado.sem_conteudo) == (0, 1)


def test_video_que_cobre_duas_ementas_e_um_so(db: Session, cliente_yt: ClienteYoutube) -> None:
    lacunas(db, "Laços de repetição")
    buscar(db, cliente_yt)
    lacunas(db, "Repetição com while")

    buscar(db, cliente_yt)

    assert db.scalar(select(func.count()).select_from(VideoYoutube)) == 1
    [video] = db.scalars(select(VideoYoutube))
    assert len(video.lacunas) == 2


# --- cota e cache -------------------------------------------------------------------------


def test_mesma_consulta_nao_gasta_cota_de_novo(
    db: Session, cliente_yt: ClienteYoutube, api: ApiFalsa, redis_falso: fakeredis.FakeRedis
) -> None:
    cliente_yt.playlists("Algoritmos aulas")
    cliente_yt.playlists("Algoritmos aulas")

    assert len(api.chamadas) == 1
    assert db.scalar(select(func.count()).select_from(BuscaYoutube)) == 1
    assert [int(v) for v in map(redis_falso.get, redis_falso.keys("algorise:youtube:cota:*"))] == [
        100
    ]


def test_cota_do_dia_acabou_e_o_resto_fica_pendente(
    db: Session, api: ApiFalsa, redis_falso: fakeredis.FakeRedis
) -> None:
    lacunas(db, "Laços de repetição", "Recursão")
    # Dá para a busca de playlists (100) e as listas (1 cada), não para a avulsa.
    cliente = ClienteYoutube(db, "chave", cota_diaria=150, transport=httpx2.MockTransport(api))

    resultado = buscar(db, cliente)

    assert resultado.interrompida
    db.expire_all()
    estados = {lacuna.assunto: lacuna.status for lacuna in db.scalars(select(Lacuna))}
    # As duas playlists cobrem uma lacuna cada: fica a primeira, da recursão, e
    # a busca avulsa dos laços já não cabe na cota.
    assert estados == {
        "Laços de repetição": StatusLacuna.pendente,
        "Recursão": StatusLacuna.em_preparacao,
    }


def test_api_recusando_por_cota_tambem_para_a_busca(
    db: Session, cliente_yt: ClienteYoutube, api: ApiFalsa
) -> None:
    api.responder = lambda _: httpx2.Response(
        403, content=b'{"error": {"errors": [{"reason": "quotaExceeded"}]}}'
    )

    with pytest.raises(CotaEsgotada):
        cliente_yt.playlists("Algoritmos aulas")


@pytest.mark.parametrize(
    ("iso", "segundos"),
    [
        ("PT59S", 59),
        ("PT15M30S", 930),
        ("PT1H2M3S", 3723),
        ("P1DT1H", 90000),
        ("P0D", None),
        ("", None),
    ],
)
def test_duracao_do_youtube_em_segundos(iso: str, segundos: int | None) -> None:
    assert duracao_em_segundos(iso) == segundos


# --- tarefa e disparo ---------------------------------------------------------------------


def test_sem_chave_da_api_a_tarefa_nao_faz_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "")

    def nao_deveria_abrir(*_args: object) -> None:
        raise AssertionError("abriu sessão sem chave")

    monkeypatch.setattr(tarefa_busca, "SessionLocal", nao_deveria_abrir)

    tarefa_busca.buscar(DISCIPLINA)


def test_tarefa_com_chave_busca_e_grava(
    sessao_factory, db: Session, api: ApiFalsa, redis_falso, monkeypatch: pytest.MonkeyPatch
) -> None:
    lacunas(db, "Laços de repetição")
    monkeypatch.setattr(settings, "youtube_api_key", "chave")
    monkeypatch.setattr(tarefa_busca, "SessionLocal", sessao_factory)
    monkeypatch.setattr(tarefa_busca, "get_provedor_ia_tarefas", ProvedorDeEmenta)
    monkeypatch.setattr(
        tarefa_busca,
        "ClienteYoutube",
        lambda db, chave: ClienteYoutube(db, chave, transport=httpx2.MockTransport(api)),
    )

    tarefa_busca.buscar(DISCIPLINA)

    db.expire_all()
    assert db.scalars(select(Lacuna)).one().status is StatusLacuna.em_preparacao


def test_busca_entra_na_fila_uma_vez_por_disciplina() -> None:
    fila = FilaRedis(fakeredis.FakeRedis(), "teste")

    assert fila.busca_de_conteudo("Introdução à Programação") is True
    assert fila.busca_de_conteudo("introducao a programacao") is False

    assert fila.fila.job_ids == ["busca-introducao-a-programacao"]


@pytest.fixture
def disparos(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    chamadas: list[str] = []

    class Espia:
        def busca_de_conteudo(self, disciplina: str) -> bool:
            chamadas.append(disciplina)
            return True

    monkeypatch.setattr(assuntos_ementa, "fila_das_tarefas", Espia)
    yield chamadas


def test_ementa_lida_dispara_a_busca_das_disciplinas_com_lacuna(
    cliente: TestClient,
    autenticado: dict[str, str],
    db: Session,
    disparos: list[str],
    tmp_path,
    monkeypatch,
) -> None:
    from app.ia import get_provedor_ia_tarefas
    from app.main import app
    from tests.test_ementa_assuntos import DISCIPLINA as DA_EMENTA
    from tests.test_ementa_assuntos import enviar

    monkeypatch.setattr(settings, "diretorio_midia", str(tmp_path))
    app.dependency_overrides[get_provedor_ia_tarefas] = ProvedorDeEmenta

    enviar(cliente, autenticado)

    # "Recursão" não tem módulo no catálogo vazio: a disciplina tem lacuna.
    assert disparos == [DA_EMENTA]
