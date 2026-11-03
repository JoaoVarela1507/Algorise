"""API administrativa: papéis, trilhas, passos, atividades, publicação e métricas (#41)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Atividade,
    Modulo,
    PapelUsuario,
    ProgressoUsuario,
    RespostaUsuario,
    StatusProgresso,
    TipoAtividade,
    Trilha,
    Usuario,
)
from app.tarefas import papeis

API = "/api/v1/admin"


@pytest.fixture
def autor(db: Session, usuario: Usuario, autenticado: dict[str, str]) -> dict[str, str]:
    """O aluno da fixture, promovido a autor de conteúdo."""
    usuario.papel = PapelUsuario.autor
    db.merge(usuario)
    db.commit()
    return autenticado


@pytest.fixture
def admin(db: Session, usuario: Usuario, autenticado: dict[str, str]) -> dict[str, str]:
    usuario.papel = PapelUsuario.admin
    db.merge(usuario)
    db.commit()
    return autenticado


@pytest.fixture
def rascunho(cliente: TestClient, autor: dict[str, str]) -> dict:
    """Uma trilha em rascunho com dois passos e uma atividade de terminal completa."""
    trilha = cliente.post(
        f"{API}/trilhas",
        headers=autor,
        json={"slug": "git", "nome": "Git", "disciplina": "Ferramentas"},
    ).json()
    um = cliente.post(
        f"{API}/trilhas/{trilha['id']}/passos", headers=autor, json={"titulo": "Clone"}
    ).json()
    cliente.post(f"{API}/trilhas/{trilha['id']}/passos", headers=autor, json={"titulo": "Commit"})
    cliente.post(
        f"{API}/atividades",
        headers=autor,
        json={
            "passo_id": um["id"],
            "tipo": "terminal",
            "enunciado": "Clone o repositório",
            "comando_esperado": "git clone url",
            "saida_esperada": "Cloning into",
        },
    )
    return cliente.get(f"{API}/trilhas", headers=autor).json()[0]


def ordens(db: Session, trilha_id: int) -> list[tuple[int, str]]:
    db.expire_all()
    return [
        (m.ordem, m.titulo)
        for m in db.scalars(
            select(Modulo).where(Modulo.trilha_id == trilha_id).order_by(Modulo.ordem)
        )
    ]


# --- papéis -------------------------------------------------------------------------------


def test_aluno_nao_entra_na_api_administrativa(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    resposta = cliente.get(f"{API}/trilhas", headers=autenticado)

    assert resposta.status_code == 403


def test_autor_mexe_no_conteudo_mas_so_admin_ve_metricas(
    cliente: TestClient, autor: dict[str, str]
) -> None:
    assert cliente.get(f"{API}/trilhas", headers=autor).status_code == 200
    assert cliente.get(f"{API}/metricas", headers=autor).status_code == 403


def test_linha_de_comando_promove_o_usuario(
    db: Session, usuario: Usuario, sessao_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(papeis, "SessionLocal", sessao_factory)

    assert papeis.main([usuario.email.upper(), "admin"]) == 0
    assert papeis.main(["ninguem@ufrpe.br", "autor"]) == 1

    db.expire_all()
    assert db.get(Usuario, usuario.id).papel is PapelUsuario.admin


# --- trilhas, passos e atividades ---------------------------------------------------------


def test_trilha_nasce_rascunho_com_passos_em_ordem_e_gabarito(rascunho: dict) -> None:
    assert (rascunho["slug"], rascunho["publicada"]) == ("git", False)
    assert [(p["ordem"], p["titulo"]) for p in rascunho["passos"]] == [(1, "Clone"), (2, "Commit")]
    # O admin vê o gabarito.
    assert rascunho["passos"][0]["atividades"][0]["comando_esperado"] == "git clone url"


def test_slug_repetido_e_recusado(
    cliente: TestClient, autor: dict[str, str], rascunho: dict
) -> None:
    resposta = cliente.post(
        f"{API}/trilhas", headers=autor, json={"slug": "git", "nome": "Outra", "disciplina": "X"}
    )

    assert (resposta.status_code, resposta.json()["erro"]["code"]) == (409, "slug_em_uso")


def test_inserir_e_mover_passo_renumera_sem_buraco(
    cliente: TestClient, autor: dict[str, str], rascunho: dict, db: Session
) -> None:
    trilha_id = rascunho["id"]
    novo = cliente.post(
        f"{API}/trilhas/{trilha_id}/passos", headers=autor, json={"titulo": "Init", "ordem": 1}
    ).json()
    assert ordens(db, trilha_id) == [(1, "Init"), (2, "Clone"), (3, "Commit")]

    cliente.patch(
        f"{API}/trilhas/{trilha_id}/passos/{novo['id']}", headers=autor, json={"ordem": 3}
    )

    assert ordens(db, trilha_id) == [(1, "Clone"), (2, "Commit"), (3, "Init")]


def test_apagar_passo_fecha_o_buraco(
    cliente: TestClient, autor: dict[str, str], rascunho: dict, db: Session
) -> None:
    primeiro = rascunho["passos"][0]["id"]

    resposta = cliente.delete(f"{API}/trilhas/{rascunho['id']}/passos/{primeiro}", headers=autor)

    assert resposta.status_code == 204
    assert ordens(db, rascunho["id"]) == [(1, "Commit")]


def test_passo_com_progresso_nao_se_apaga(
    cliente: TestClient, autor: dict[str, str], rascunho: dict, db: Session, usuario: Usuario
) -> None:
    passo = rascunho["passos"][0]["id"]
    db.add(
        ProgressoUsuario(
            usuario_id=usuario.id,
            trilha_id=rascunho["id"],
            modulo_id=passo,
            status=StatusProgresso.concluido,
        )
    )
    db.commit()

    passo_resposta = cliente.delete(f"{API}/trilhas/{rascunho['id']}/passos/{passo}", headers=autor)
    trilha_resposta = cliente.delete(f"{API}/trilhas/{rascunho['id']}", headers=autor)

    assert (passo_resposta.status_code, trilha_resposta.status_code) == (409, 409)
    assert passo_resposta.json()["erro"]["code"] == "conteudo_com_progresso"


def test_atividade_respondida_nao_se_apaga(
    cliente: TestClient, autor: dict[str, str], rascunho: dict, db: Session, usuario: Usuario
) -> None:
    atividade = rascunho["passos"][0]["atividades"][0]["id"]
    db.add(RespostaUsuario(usuario_id=usuario.id, atividade_id=atividade, conteudo="git clone"))
    db.commit()

    resposta = cliente.delete(f"{API}/atividades/{atividade}", headers=autor)

    assert resposta.status_code == 409


# --- publicação ---------------------------------------------------------------------------


def test_publicar_confere_o_gabarito(
    cliente: TestClient, autor: dict[str, str], rascunho: dict
) -> None:
    passo = rascunho["passos"][1]["id"]
    cliente.post(
        f"{API}/atividades",
        headers=autor,
        json={"passo_id": passo, "tipo": "terminal", "enunciado": "Faça um commit"},
    )

    recusada = cliente.post(
        f"{API}/trilhas/{rascunho['id']}/publicar", headers=autor, json={"publicada": True}
    )

    assert recusada.status_code == 422
    assert recusada.json()["erro"]["details"]["problemas"] == [
        {
            "passo": 2,
            "atividade": 1,
            "problema": "A atividade de terminal precisa do comando esperado.",
        }
    ]


def test_trilha_publicada_aparece_no_catalogo_e_nao_aceita_atividade_sem_gabarito(
    cliente: TestClient, autor: dict[str, str], rascunho: dict
) -> None:
    publicada = cliente.post(
        f"{API}/trilhas/{rascunho['id']}/publicar", headers=autor, json={"publicada": True}
    )
    assert (publicada.status_code, publicada.json()["publicada"]) == (200, True)
    assert cliente.get("/api/v1/trilhas/git").status_code == 200

    sem_gabarito = cliente.post(
        f"{API}/atividades",
        headers=autor,
        json={
            "passo_id": rascunho["passos"][1]["id"],
            "tipo": "resposta-aberta",
            "enunciado": "Explique",
        },
    )

    assert sem_gabarito.status_code == 422


def test_trilha_sem_passo_nao_publica(cliente: TestClient, autor: dict[str, str]) -> None:
    trilha = cliente.post(
        f"{API}/trilhas", headers=autor, json={"slug": "vazia", "nome": "Vazia", "disciplina": "X"}
    ).json()

    resposta = cliente.post(
        f"{API}/trilhas/{trilha['id']}/publicar", headers=autor, json={"publicada": True}
    )

    assert resposta.json()["erro"]["details"]["problemas"] == [
        {"problema": "A trilha não tem nenhum passo."}
    ]


def test_previa_mostra_o_passo_como_o_aluno_ve(
    cliente: TestClient, autor: dict[str, str], rascunho: dict
) -> None:
    previa = cliente.get(f"{API}/passos/{rascunho['passos'][0]['id']}/previa", headers=autor).json()

    assert (previa["titulo"], previa["bloqueado"], previa["proximo"]) == ("Clone", False, 2)
    assert "comando_esperado" not in previa["atividades"][0]


# --- importação ---------------------------------------------------------------------------


TRILHA_IMPORTADA = {
    "slug": "sql",
    "nome": "SQL",
    "disciplina": "Banco de Dados",
    "periodo": 3,
    "publicada": True,
    "passos": [
        {
            "titulo": "SELECT",
            "atividades": [
                {
                    "tipo": "terminal",
                    "enunciado": "Liste a tabela",
                    "comando_esperado": "SELECT * FROM aluno;",
                    "saida_esperada": "3 linhas",
                }
            ],
        },
        {"titulo": "WHERE"},
    ],
}


def test_importar_cria_e_importar_de_novo_atualiza(
    cliente: TestClient, autor: dict[str, str], db: Session
) -> None:
    primeira = cliente.post(f"{API}/trilhas/importar", headers=autor, json=TRILHA_IMPORTADA)
    assert (primeira.status_code, primeira.json()["publicada"]) == (200, True)

    mudada = {
        **TRILHA_IMPORTADA,
        "passos": [{**TRILHA_IMPORTADA["passos"][0], "titulo": "SELECT básico"}],
    }
    segunda = cliente.post(f"{API}/trilhas/importar", headers=autor, json=mudada).json()

    assert segunda["id"] == primeira.json()["id"]
    assert [p["titulo"] for p in segunda["passos"]] == ["SELECT básico"]
    assert len(db.scalars(select(Trilha).where(Trilha.slug == "sql")).all()) == 1


def test_importacao_publicada_com_gabarito_faltando_e_recusada_inteira(
    cliente: TestClient, autor: dict[str, str], db: Session
) -> None:
    quebrada = {
        **TRILHA_IMPORTADA,
        "passos": [
            {"titulo": "X", "atividades": [{"tipo": "terminal", "enunciado": "Sem gabarito"}]}
        ],
    }

    resposta = cliente.post(f"{API}/trilhas/importar", headers=autor, json=quebrada)

    assert resposta.status_code == 422
    assert db.scalar(select(Trilha).where(Trilha.slug == "sql")) is None


# --- métricas -----------------------------------------------------------------------------


def test_metricas_de_conclusao_acerto_abandono_e_erros_comuns(
    cliente: TestClient, admin: dict[str, str], db: Session, usuario: Usuario
) -> None:
    trilha = Trilha(slug="m", nome="M", disciplina="X", publicada=True)
    passo = Modulo(ordem=1, titulo="Um")
    passo.atividades = [
        Atividade(
            ordem=1,
            tipo=TipoAtividade.terminal,
            enunciado="e",
            comando_esperado="ls",
            saida_esperada="a",
        )
    ]
    trilha.modulos = [passo]
    outro = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add_all([trilha, outro])
    db.commit()
    atividade = passo.atividades[0]
    db.add_all(
        [
            ProgressoUsuario(
                usuario_id=usuario.id,
                trilha_id=trilha.id,
                modulo_id=passo.id,
                status=StatusProgresso.concluido,
            ),
            ProgressoUsuario(
                usuario_id=outro.id,
                trilha_id=trilha.id,
                modulo_id=passo.id,
                status=StatusProgresso.em_andamento,
            ),
            RespostaUsuario(
                usuario_id=usuario.id, atividade_id=atividade.id, conteudo="sl", correta=False
            ),
            RespostaUsuario(
                usuario_id=usuario.id, atividade_id=atividade.id, conteudo="ls", correta=True
            ),
            RespostaUsuario(
                usuario_id=outro.id, atividade_id=atividade.id, conteudo="sl", correta=False
            ),
        ]
    )
    db.commit()

    [metricas] = [
        m for m in cliente.get(f"{API}/metricas", headers=admin).json() if m["slug"] == "m"
    ]

    assert (
        metricas["alunos_iniciaram"],
        metricas["alunos_concluiram"],
        metricas["taxa_de_conclusao"],
    ) == (2, 1, 0.5)
    [da_atividade] = metricas["atividades"]
    assert (da_atividade["tentativas"], da_atividade["acertos"], da_atividade["abandono"]) == (
        3,
        1,
        0.5,
    )
    assert da_atividade["erros_comuns"] == [{"resposta": "sl", "vezes": 2}]
