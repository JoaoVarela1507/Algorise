"""Vídeo assistido e transcrição do passo (#21)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import DocumentoVault, Modulo, OrigemVault, TrechoVault, Trilha
from app.services.transcricao_do_passo import _sem_sobreposicao


@pytest.fixture
def trilha_com_video(db: Session) -> Trilha:
    trilha = Trilha(slug="laços", nome="Laços", disciplina="Algoritmos", periodo=1, publicada=True)
    for ordem in (1, 2):
        trilha.modulos.append(
            Modulo(
                ordem=ordem,
                titulo=f"Passo {ordem}",
                video_url="https://www.youtube.com/watch?v=abcdefghijk",
            )
        )
    db.add(trilha)
    db.commit()
    return trilha


def test_marcar_video_assistido_vai_para_o_passo_e_e_idempotente(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_video: Trilha
) -> None:
    rota = f"/api/v1/trilhas/{trilha_com_video.slug}/passos/1"
    assert cliente.get(rota, headers=autenticado).json()["video_assistido"] is False

    primeira = cliente.post(f"{rota}/video-assistido", headers=autenticado)
    segunda = cliente.post(f"{rota}/video-assistido", headers=autenticado)

    assert primeira.status_code == 200
    # Repetir guarda a data da primeira vez.
    assert segunda.json()["video_assistido_em"] == primeira.json()["video_assistido_em"]
    assert cliente.get(rota, headers=autenticado).json()["video_assistido"] is True


def test_video_assistido_pede_login_e_respeita_o_bloqueio(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_video: Trilha
) -> None:
    rota = f"/api/v1/trilhas/{trilha_com_video.slug}/passos"
    assert cliente.post(f"{rota}/1/video-assistido").status_code == 401
    # O passo 2 ainda está fechado para quem não concluiu o 1.
    assert cliente.post(f"{rota}/2/video-assistido", headers=autenticado).status_code == 403


def test_sem_transcricao_a_lista_vem_vazia(cliente: TestClient, trilha_com_video: Trilha) -> None:
    resposta = cliente.get(f"/api/v1/trilhas/{trilha_com_video.slug}/passos/1/transcricao")

    assert resposta.status_code == 200
    assert resposta.json() == {"falas": []}


def test_transcricao_do_modulo_vem_na_ordem_e_sem_a_sobreposicao(
    cliente: TestClient, db: Session, trilha_com_video: Trilha
) -> None:
    modulo = trilha_com_video.modulos[0]
    documento = DocumentoVault(
        origem=OrigemVault.transcricao,
        chave=f"modulo:{modulo.id}",
        titulo="Aula",
        modulo_id=modulo.id,
        hash_conteudo="x",
    )
    documento.trechos = [
        TrechoVault(
            ordem=0,
            texto="Um laço repete um bloco. O for percorre a lista.",
            inicio_segundos=0.0,
            fim_segundos=12.0,
            embedding=[0.0] * 1024,
        ),
        # Repete o fim do anterior ("O for percorre a lista."), como o vault faz.
        TrechoVault(
            ordem=1,
            texto="O for percorre a lista. O while repete enquanto a condição vale.",
            inicio_segundos=10.0,
            fim_segundos=25.0,
            embedding=[0.0] * 1024,
        ),
    ]
    db.add(documento)
    db.commit()

    falas = cliente.get(f"/api/v1/trilhas/{trilha_com_video.slug}/passos/1/transcricao").json()[
        "falas"
    ]

    assert [f["texto"] for f in falas] == [
        "Um laço repete um bloco. O for percorre a lista.",
        "O while repete enquanto a condição vale.",
    ]
    assert [f["inicio"] for f in falas] == [0.0, 10.0]


def test_sobreposicao_so_sai_quando_repete_de_fato() -> None:
    assert _sem_sobreposicao("a b c", "c d e") == "d e"
    assert _sem_sobreposicao("a b c", "x y z") == "x y z"
    assert _sem_sobreposicao("", " primeira fala ") == "primeira fala"
