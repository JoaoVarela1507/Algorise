"""Testes do catálogo, do caminho da trilha e do desbloqueio sequencial (#29).

O que mais importa aqui é a última parte: o cadeado da tela 26 é decoração, e
quem decide o que está aberto é o servidor. Um aluno que chame
`GET /trilhas/x/passos/7` direto precisa levar 403.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Atividade, Modulo, TipoAtividade, Trilha, Usuario
from app.services import progresso
from app.services import trilhas as servico
from tests.conftest import SENHA_VALIDA


@pytest.fixture
def trilha_com_passos(db: Session) -> Trilha:
    """Trilha publicada com três passos, cada um com uma atividade."""
    trilha = Trilha(
        slug="logica",
        nome="Lógica de Programação",
        disciplina="Algoritmos",
        categoria="Fundamentos",
        periodo=1,
        publicada=True,
    )
    for ordem in (1, 2, 3):
        modulo = Modulo(ordem=ordem, titulo=f"Passo {ordem}", descricao=f"Conteúdo {ordem}")
        modulo.atividades.append(
            Atividade(
                ordem=1,
                tipo=TipoAtividade.terminal,
                enunciado=f"Enunciado do passo {ordem}",
                comando_esperado="python --version",
                xp=10,
            )
        )
        trilha.modulos.append(modulo)

    db.add(trilha)
    db.commit()
    return trilha


def concluir(db: Session, usuario: Usuario, trilha: Trilha, ordem: int) -> None:
    modulo = next(m for m in trilha.modulos if m.ordem == ordem)
    progresso.concluir_passo(db, usuario_id=usuario.id, trilha=trilha, modulo=modulo)


# --------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------


def test_catalogo_filtra_por_categoria(
    cliente: TestClient, db: Session, trilha_com_passos: Trilha
) -> None:
    db.add(
        Trilha(
            slug="banco",
            nome="Banco de Dados",
            disciplina="Dados",
            categoria="Dados",
            periodo=3,
            publicada=True,
        )
    )
    db.commit()

    corpo = cliente.get("/api/v1/trilhas", params={"categoria": "Fundamentos"}).json()

    assert [item["slug"] for item in corpo["itens"]] == ["logica"]
    assert corpo["total"] == 1


def test_filtro_de_categoria_ignora_maiusculas(
    cliente: TestClient, trilha_com_passos: Trilha
) -> None:
    corpo = cliente.get("/api/v1/trilhas", params={"categoria": "fUNDAMENTOS"}).json()

    assert corpo["total"] == 1


def test_catalogo_sem_token_responde_sem_progresso(
    cliente: TestClient, trilha_com_passos: Trilha
) -> None:
    corpo = cliente.get("/api/v1/trilhas").json()

    assert corpo["itens"][0]["progresso"] == 0
    assert corpo["itens"][0]["total_modulos"] == 3


def test_catalogo_traz_o_progresso_do_aluno(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    concluir(db, usuario, trilha_com_passos, 1)

    corpo = cliente.get("/api/v1/trilhas", headers=autenticado).json()

    assert corpo["itens"][0]["progresso"] == 1
    assert corpo["itens"][0]["total_modulos"] == 3


def test_progresso_nao_vaza_entre_alunos(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    """O catálogo fica num cache compartilhado; o progresso é sobreposto depois.

    Este teste existe para o dia em que alguém pensar em pôr o progresso dentro
    da chave do cache: com um aluno vendo o "3/10" do outro, ele falha.
    """
    concluir(db, usuario, trilha_com_passos, 1)
    cliente.get("/api/v1/trilhas", headers=autenticado)

    outro = cliente.post(
        "/api/v1/auth/register",
        json={
            "username": "bia",
            "email": "bia@ufrpe.br",
            "senha": SENHA_VALIDA,
            "aceite_termos": True,
        },
    ).json()

    corpo = cliente.get(
        "/api/v1/trilhas", headers={"Authorization": f"Bearer {outro['access_token']}"}
    ).json()

    assert corpo["itens"][0]["progresso"] == 0


def test_progresso_aparece_mesmo_com_o_cache_quente(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    """O #29 pedia invalidar o catálogo quando o progresso muda.

    Com o progresso fora do cache, não há o que invalidar: a página vem do
    Redis e o "3/10" é calculado no request. Este teste é o que aquela tarefa
    queria garantir — esquentar o cache e concluir um passo em seguida, e o
    número já sai certo.
    """
    assert cliente.get("/api/v1/trilhas", headers=autenticado).json()["itens"][0]["progresso"] == 0

    concluir(db, usuario, trilha_com_passos, 1)

    depois = cliente.get("/api/v1/trilhas", headers=autenticado).json()
    assert depois["itens"][0]["progresso"] == 1


def test_token_invalido_no_catalogo_e_tratado_como_visitante(
    cliente: TestClient, trilha_com_passos: Trilha
) -> None:
    """Recusar a página por causa de um token vencido esconderia conteúdo público."""
    resposta = cliente.get("/api/v1/trilhas", headers={"Authorization": "Bearer nao-e-token"})

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1


# --------------------------------------------------------------------------
# Detalhe e estados dos passos
# --------------------------------------------------------------------------


def test_primeiro_passo_nasce_liberado(cliente: TestClient, trilha_com_passos: Trilha) -> None:
    corpo = cliente.get("/api/v1/trilhas/logica").json()

    estados = [modulo["status"] for modulo in corpo["modulos"]]
    assert estados == ["em-andamento", "bloqueado", "bloqueado"]


def test_concluir_um_passo_abre_o_seguinte(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    concluir(db, usuario, trilha_com_passos, 1)

    corpo = cliente.get("/api/v1/trilhas/logica", headers=autenticado).json()

    estados = [modulo["status"] for modulo in corpo["modulos"]]
    assert estados == ["concluido", "em-andamento", "bloqueado"]
    assert corpo["progresso"] == 1


def test_booleanos_acompanham_o_status(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    concluir(db, usuario, trilha_com_passos, 1)

    modulos = cliente.get("/api/v1/trilhas/logica", headers=autenticado).json()["modulos"]

    assert (modulos[0]["concluido"], modulos[0]["bloqueado"]) == (True, False)
    assert (modulos[1]["concluido"], modulos[1]["bloqueado"]) == (False, False)
    assert (modulos[2]["concluido"], modulos[2]["bloqueado"]) == (False, True)


def test_trilha_nao_publicada_responde_404(cliente: TestClient, db: Session) -> None:
    """Quem não pode vê-la não precisa saber que ela existe."""
    db.add(Trilha(slug="rascunho", nome="Rascunho", disciplina="X", publicada=False))
    db.commit()

    resposta = cliente.get("/api/v1/trilhas/rascunho")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "trilha_nao_encontrada"


# --------------------------------------------------------------------------
# Conteúdo do passo e desbloqueio
# --------------------------------------------------------------------------


def test_passo_liberado_devolve_o_conteudo(cliente: TestClient, trilha_com_passos: Trilha) -> None:
    corpo = cliente.get("/api/v1/trilhas/logica/passos/1").json()

    assert corpo["titulo"] == "Passo 1"
    assert corpo["trilha_nome"] == "Lógica de Programação"
    assert corpo["total_passos"] == 3
    assert corpo["proximo"] == 2
    assert corpo["atividades"][0]["enunciado"] == "Enunciado do passo 1"


def test_passo_bloqueado_responde_403(cliente: TestClient, trilha_com_passos: Trilha) -> None:
    """O cadeado da tela é decoração: a regra vale mesmo chamando a API direto."""
    resposta = cliente.get("/api/v1/trilhas/logica/passos/3")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["code"] == "passo_bloqueado"


def test_passo_abre_depois_de_concluir_o_anterior(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    assert cliente.get("/api/v1/trilhas/logica/passos/2", headers=autenticado).status_code == 403

    concluir(db, usuario, trilha_com_passos, 1)

    assert cliente.get("/api/v1/trilhas/logica/passos/2", headers=autenticado).status_code == 200


def test_ultimo_passo_nao_tem_proximo(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    concluir(db, usuario, trilha_com_passos, 1)
    concluir(db, usuario, trilha_com_passos, 2)

    corpo = cliente.get("/api/v1/trilhas/logica/passos/3", headers=autenticado).json()

    assert corpo["proximo"] is None


def test_passo_inexistente_responde_404(cliente: TestClient, trilha_com_passos: Trilha) -> None:
    resposta = cliente.get("/api/v1/trilhas/logica/passos/99")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "passo_nao_encontrado"


def test_o_gabarito_nunca_vai_para_o_cliente(
    cliente: TestClient, trilha_com_passos: Trilha
) -> None:
    """`comando_esperado` é resposta: mandá-lo antes da submissão entrega tudo (#30)."""
    passo = cliente.get("/api/v1/trilhas/logica/passos/1")
    detalhe = cliente.get("/api/v1/trilhas/logica")

    for resposta in (passo, detalhe):
        assert "comando_esperado" not in resposta.text
        assert "python --version" not in resposta.text


# --------------------------------------------------------------------------
# Iniciar
# --------------------------------------------------------------------------


def test_iniciar_exige_autenticacao(cliente: TestClient, trilha_com_passos: Trilha) -> None:
    assert cliente.post("/api/v1/trilhas/logica/iniciar").status_code == 401


def test_iniciar_devolve_a_trilha_com_o_primeiro_passo_aberto(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_passos: Trilha
) -> None:
    corpo = cliente.post("/api/v1/trilhas/logica/iniciar", headers=autenticado).json()

    assert corpo["modulos"][0]["status"] == "em-andamento"
    assert corpo["progresso"] == 0


def test_iniciar_de_novo_nao_apaga_o_progresso(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    cliente.post("/api/v1/trilhas/logica/iniciar", headers=autenticado)
    concluir(db, usuario, trilha_com_passos, 1)

    corpo = cliente.post("/api/v1/trilhas/logica/iniciar", headers=autenticado).json()

    assert corpo["progresso"] == 1
    assert corpo["modulos"][0]["status"] == "concluido"


# --------------------------------------------------------------------------
# Recomendadas
# --------------------------------------------------------------------------


@pytest.fixture
def catalogo_por_periodo(db: Session) -> None:
    for periodo in (1, 2, 5):
        db.add(
            Trilha(
                slug=f"trilha-p{periodo}",
                nome=f"Trilha do {periodo}º",
                disciplina="Algoritmos",
                periodo=periodo,
                publicada=True,
            )
        )
    db.commit()


def test_recomendadas_exigem_autenticacao(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/trilhas/recomendadas").status_code == 401


def test_recomendadas_priorizam_o_periodo_do_aluno(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    catalogo_por_periodo: None,
) -> None:
    usuario.periodo = 2
    db.commit()

    corpo = cliente.get("/api/v1/trilhas/recomendadas", headers=autenticado).json()

    assert corpo[0]["slug"] == "trilha-p2"
    assert corpo[0]["motivo"] == servico.MOTIVO_PERIODO
    assert corpo[1]["slug"] == "trilha-p5" or corpo[1]["motivo"] != servico.MOTIVO_PERIODO


def test_recomendadas_mudam_com_o_periodo(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    catalogo_por_periodo: None,
) -> None:
    usuario.periodo = 1
    db.commit()
    primeiro = cliente.get("/api/v1/trilhas/recomendadas", headers=autenticado).json()

    usuario.periodo = 5
    db.commit()
    quinto = cliente.get("/api/v1/trilhas/recomendadas", headers=autenticado).json()

    assert primeiro[0]["slug"] != quinto[0]["slug"]


def test_trilha_concluida_sai_das_recomendacoes(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    for ordem in (1, 2, 3):
        concluir(db, usuario, trilha_com_passos, ordem)

    corpo = cliente.get("/api/v1/trilhas/recomendadas", headers=autenticado).json()

    assert all(item["slug"] != "logica" for item in corpo)


def test_recomendada_traz_o_motivo(
    cliente: TestClient, autenticado: dict[str, str], catalogo_por_periodo: None
) -> None:
    corpo = cliente.get("/api/v1/trilhas/recomendadas", headers=autenticado).json()

    assert corpo, "o catálogo do teste tem trilhas"
    assert all(item["motivo"] for item in corpo)
