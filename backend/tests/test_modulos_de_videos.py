"""Partes de vídeo aprovadas viram módulos da trilha, e os alunos reportam (#210)."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import fila as nucleo_fila
from app.models import (
    AssuntoEmenta,
    DisciplinaEmenta,
    Ementa,
    Lacuna,
    Modulo,
    NivelExperiencia,
    OrigemModulo,
    ParteVideo,
    StatusAssuntos,
    StatusEmenta,
    StatusLacuna,
    Trilha,
    Usuario,
    VideoLacuna,
    VideoYoutube,
)
from app.services import modulos_de_videos, trilha_guiada


@pytest.fixture(autouse=True)
def sem_redis_de_verdade(redis_falso) -> None:
    """Publicar e remover invalidam o catálogo em cache: com o Redis falso, na hora."""


@pytest.fixture
def algoritmos(db: Session) -> Trilha:
    trilha = Trilha(slug="algoritmos", nome="Algoritmos", disciplina="Algoritmos", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Boas-vindas")]
    db.add(trilha)
    db.commit()
    return trilha


@pytest.fixture
def video(db: Session) -> VideoYoutube:
    """Duas partes aprovadas de Algoritmos e uma descartada, cada aprovada com uma lacuna."""
    lacos = Lacuna(chave="algoritmos|lacos", disciplina="Algoritmos", assunto="Laços")
    funcoes = Lacuna(chave="algoritmos|funcoes", disciplina="ALGORITMOS", assunto="Funções")
    registro = VideoYoutube(youtube_id="abc123", titulo="Python", canal="Prof. Ana")
    registro.lacunas = [
        VideoLacuna(lacuna=lacos, distancia=0.1),
        VideoLacuna(lacuna=funcoes, distancia=0.2),
    ]
    registro.partes = [
        ParteVideo(
            ordem=0,
            inicio_segundos=60,
            fim_segundos=600,
            titulo="Laços",
            resumo="for e while",
            disciplina="Algoritmos",
            aprovada=True,
            lacunas=[lacos],
        ),
        ParteVideo(
            ordem=1, inicio_segundos=600, fim_segundos=700, titulo="Inscreva-se", aprovada=False
        ),
        ParteVideo(
            ordem=2,
            inicio_segundos=700,
            fim_segundos=1500,
            titulo="Funções",
            disciplina="algoritmos",
            aprovada=True,
            lacunas=[funcoes],
        ),
    ]
    for lacuna in (lacos, funcoes):
        lacuna.status = StatusLacuna.em_preparacao
    db.add(registro)
    db.commit()
    return registro


def aluno(db: Session, nome: str) -> Usuario:
    """Direto no banco, sem senha: o hash de três cadastros custaria segundos ao teste."""
    registro = Usuario(email=f"{nome}@ufrpe.br", username=nome, nome_exibicao=nome)
    db.add(registro)
    db.commit()
    return registro


# --- publicação ---------------------------------------------------------------------------


def test_partes_aprovadas_viram_modulos_no_fim_da_trilha_da_disciplina(
    db: Session, algoritmos: Trilha, video: VideoYoutube
) -> None:
    """O critério da #210, no backend."""
    novos = modulos_de_videos.publicar(db, video)

    assert [(m.ordem, m.titulo, m.inicio_segundos, m.fim_segundos) for m in novos] == [
        (2, "Laços", 60, 600),
        (3, "Funções", 700, 1500),
    ]
    lacos = novos[0]
    assert (lacos.trilha_id, lacos.origem, lacos.canal, lacos.descricao) == (
        algoritmos.id,
        OrigemModulo.youtube,
        "Prof. Ana",
        "for e while",
    )
    assert lacos.video_url == "https://www.youtube.com/watch?v=abc123"
    lacunas = {lacuna.assunto: lacuna for lacuna in db.scalars(select(Lacuna))}
    assert {a: (lac.status, lac.modulo_id) for a, lac in lacunas.items()} == {
        "Laços": (StatusLacuna.coberta, novos[0].id),
        "Funções": (StatusLacuna.coberta, novos[1].id),
    }


def test_publicar_de_novo_nao_duplica(db: Session, algoritmos: Trilha, video: VideoYoutube) -> None:
    modulos_de_videos.publicar(db, video)

    assert modulos_de_videos.publicar(db, video) == []
    assert len(db.scalars(select(Modulo).where(Modulo.trilha_id == algoritmos.id)).all()) == 3


def test_disciplina_sem_trilha_ganha_uma_publicada(db: Session, video: VideoYoutube) -> None:
    db.add(Trilha(slug="algoritmos", nome="Outra", disciplina="Cálculo", publicada=True))
    db.commit()

    [primeiro, _] = modulos_de_videos.publicar(db, video)

    trilha = primeiro.trilha
    assert (trilha.slug, trilha.disciplina, trilha.publicada, primeiro.ordem) == (
        "algoritmos-2",
        "Algoritmos",
        True,
        1,
    )


def test_passo_do_modulo_automatico_traz_o_intervalo_e_o_canal(
    cliente: TestClient, autenticado: dict[str, str], db: Session, algoritmos, video
) -> None:
    modulos_de_videos.publicar(db, video)

    passo = cliente.get("/api/v1/trilhas/algoritmos/passos/2", headers=autenticado)

    # Passo 2 depende do 1 na ordem do catálogo; o aluno é da guiada.
    assert passo.status_code in (200, 403)
    detalhe = cliente.get("/api/v1/trilhas/algoritmos", headers=autenticado).json()
    modulo = detalhe["modulos"][1]
    assert (
        modulo["inicio_segundos"],
        modulo["fim_segundos"],
        modulo["origem"],
        modulo["canal"],
    ) == (
        60,
        600,
        "youtube",
        "Prof. Ana",
    )
    assert detalhe["modulos"][0]["origem"] == "manual"


def test_trilha_guiada_mostra_o_modulo_no_lugar_da_lacuna_coberta(
    db: Session, algoritmos: Trilha, video: VideoYoutube, usuario: Usuario
) -> None:
    # No nível baixo, o "Boas-vindas" entraria antes, como base.
    usuario.nivel_experiencia = NivelExperiencia.medio
    lacos = db.scalars(select(Lacuna).where(Lacuna.assunto == "Laços")).one()
    ementa = Ementa(
        usuario_id=usuario.id,
        arquivo_path="x.pdf",
        status=StatusEmenta.processada,
        status_assuntos=StatusAssuntos.prontos,
        confirmada_em=datetime.now(UTC),
    )
    ementa.disciplinas = [
        DisciplinaEmenta(
            ordem=0,
            nome="Algoritmos",
            na_trilha=True,
            assuntos=[AssuntoEmenta(ordem=0, texto="Laços", lacuna=lacos)],
        )
    ]
    db.add(ementa)
    db.commit()
    assert trilha_guiada.montar(db, usuario)[1][0].lacuna is not None

    modulos_de_videos.publicar(db, video)
    db.expire_all()

    [item] = trilha_guiada.montar(db, usuario)[1]
    assert (item.modulo.titulo, item.assuntos) == ("Laços", ["Laços"])


# --- reportes -----------------------------------------------------------------------------


def test_tres_alunos_reportam_e_o_modulo_sai_da_trilha(
    db: Session, algoritmos: Trilha, video: VideoYoutube, monkeypatch: pytest.MonkeyPatch
) -> None:
    buscas: list[str] = []

    class Espia:
        def busca_de_conteudo(self, disciplina: str) -> bool:
            buscas.append(disciplina)
            return True

    monkeypatch.setattr(nucleo_fila, "fila_das_tarefas", Espia)
    lacos, funcoes = modulos_de_videos.publicar(db, video)

    resultados = [
        modulos_de_videos.reportar(db, aluno(db, nome), lacos) for nome in ("ana", "bia", "caio")
    ]

    assert resultados == [(1, False), (2, False), (3, True)]
    db.expire_all()
    restantes = db.scalars(
        select(Modulo).where(Modulo.trilha_id == algoritmos.id).order_by(Modulo.ordem)
    ).all()
    # O passo de funções sobe para o lugar do que saiu.
    assert [(m.ordem, m.titulo) for m in restantes] == [(1, "Boas-vindas"), (2, "Funções")]
    lacuna = db.scalars(select(Lacuna).where(Lacuna.assunto == "Laços")).one()
    assert (lacuna.status, lacuna.modulo_id) == (StatusLacuna.pendente, None)
    ligacao = db.scalars(select(VideoLacuna).where(VideoLacuna.lacuna_id == lacuna.id)).one()
    assert ligacao.recusada is True
    assert db.get(ParteVideo, video.partes[0].id).aprovada is False
    assert buscas == ["Algoritmos"]
    assert funcoes.id is not None


def test_mesmo_aluno_reportando_de_novo_conta_uma_vez(
    db: Session, algoritmos: Trilha, video: VideoYoutube
) -> None:
    [lacos, _] = modulos_de_videos.publicar(db, video)
    ana = aluno(db, "ana")

    modulos_de_videos.reportar(db, ana, lacos)

    assert modulos_de_videos.reportar(db, ana, lacos) == (1, False)


def test_rota_de_reportar(
    cliente: TestClient, autenticado: dict[str, str], db: Session, algoritmos, video
) -> None:
    modulos_de_videos.publicar(db, video)

    automatico = cliente.post("/api/v1/trilhas/algoritmos/passos/2/reportar", headers=autenticado)
    manual = cliente.post("/api/v1/trilhas/algoritmos/passos/1/reportar", headers=autenticado)
    inexistente = cliente.post("/api/v1/trilhas/algoritmos/passos/9/reportar", headers=autenticado)

    assert (automatico.status_code, automatico.json()) == (200, {"reportes": 1, "removido": False})
    assert (manual.status_code, manual.json()["erro"]["code"]) == (409, "modulo_nao_reportavel")
    assert inexistente.status_code == 404
