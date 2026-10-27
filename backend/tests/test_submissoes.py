"""Testes das submissões de atividade (#30).

Dois pontos concentram o risco aqui: o gabarito não pode sair da API antes da
submissão, e o XP não pode ser pago duas vezes pela mesma atividade.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Atividade, Modulo, TipoAtividade, Trilha, Usuario, XPEvento
from app.services import progresso, submissoes
from tests.conftest import SENHA_VALIDA

COMANDO = "python --version"


@pytest.fixture
def trilha_com_atividades(db: Session) -> Trilha:
    """Dois passos: o primeiro com duas atividades de terminal e uma aberta."""
    trilha = Trilha(
        slug="logica", nome="Lógica", disciplina="Algoritmos", periodo=1, publicada=True
    )

    primeiro = Modulo(ordem=1, titulo="Primeiro passo")
    primeiro.atividades.append(
        Atividade(
            ordem=1,
            tipo=TipoAtividade.terminal,
            enunciado="Veja a versão do Python",
            dica="Está no vídeo",
            comando_esperado=COMANDO,
            saida_esperada="Python 3.14.0",
            xp=10,
        )
    )
    primeiro.atividades.append(
        Atividade(
            ordem=2,
            tipo=TipoAtividade.terminal,
            enunciado="Instale o Python",
            comando_esperado="winget install Python.Python.3.14",
            xp=15,
        )
    )
    primeiro.atividades.append(
        Atividade(
            ordem=3,
            tipo=TipoAtividade.resposta_aberta,
            enunciado="Explique o que é uma flag",
            resposta_esperada="Flags modificam o comportamento de um comando.",
            xp=20,
        )
    )

    segundo = Modulo(ordem=2, titulo="Segundo passo")
    segundo.atividades.append(
        Atividade(
            ordem=1,
            tipo=TipoAtividade.terminal,
            enunciado="Rode o script",
            comando_esperado="python main.py",
            xp=10,
        )
    )

    trilha.modulos.extend([primeiro, segundo])
    db.add(trilha)
    db.commit()
    return trilha


def ids(trilha: Trilha, passo: int, atividade: int) -> int:
    modulo = next(m for m in trilha.modulos if m.ordem == passo)
    return next(a for a in modulo.atividades if a.ordem == atividade).id


# --------------------------------------------------------------------------
# Enunciado
# --------------------------------------------------------------------------


def test_enunciado_nao_traz_o_gabarito(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    """Se viesse, bastaria abrir o devtools para ter a resposta."""
    resposta = cliente.get(
        f"/api/v1/atividades/{ids(trilha_com_atividades, 1, 1)}", headers=autenticado
    )

    assert resposta.status_code == 200
    assert resposta.json()["enunciado"] == "Veja a versão do Python"
    assert COMANDO not in resposta.text
    assert "comando_esperado" not in resposta.text
    assert "saida_esperada" not in resposta.text


def test_enunciado_exige_autenticacao(cliente: TestClient, trilha_com_atividades: Trilha) -> None:
    assert cliente.get(f"/api/v1/atividades/{ids(trilha_com_atividades, 1, 1)}").status_code == 401


def test_atividade_de_passo_bloqueado_nao_abre(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    resposta = cliente.get(
        f"/api/v1/atividades/{ids(trilha_com_atividades, 2, 1)}", headers=autenticado
    )

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["code"] == "passo_bloqueado"


def test_atividade_inexistente(cliente: TestClient, autenticado: dict[str, str]) -> None:
    resposta = cliente.get("/api/v1/atividades/9999", headers=autenticado)

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "atividade_nao_encontrada"


# --------------------------------------------------------------------------
# Submissão
# --------------------------------------------------------------------------


def submeter(cliente: TestClient, headers: dict[str, str], atividade_id: int, conteudo: str):
    return cliente.post(
        f"/api/v1/atividades/{atividade_id}/submissoes",
        headers=headers,
        json={"conteudo": conteudo, "tempo_gasto_segundos": 12},
    )


def test_comando_certo_acerta_e_paga_xp(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    resposta = submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), COMANDO)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["correta"] is True
    assert corpo["xp_ganho"] == 10
    assert corpo["xp_total"] == 10
    assert corpo["tentativa"] == 1


def test_comando_errado_nao_paga(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    corpo = submeter(
        cliente, autenticado, ids(trilha_com_atividades, 1, 1), "python ---version"
    ).json()

    assert corpo["correta"] is False
    assert corpo["xp_ganho"] == 0
    assert corpo["xp_total"] == 0


@pytest.mark.parametrize(
    "digitado",
    ["  python --version  ", "PYTHON --VERSION", "python   --version"],
    ids=["espaço nas pontas", "maiúsculas", "espaço no meio"],
)
def test_comando_aceita_variacao_de_digitacao(
    cliente: TestClient,
    autenticado: dict[str, str],
    trilha_com_atividades: Trilha,
    digitado: str,
) -> None:
    """O aluno está num terminal, não preenchendo um campo."""
    corpo = submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), digitado).json()

    assert corpo["correta"] is True


def test_acertar_de_novo_nao_paga_de_novo(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    atividade = ids(trilha_com_atividades, 1, 1)
    submeter(cliente, autenticado, atividade, COMANDO)

    segunda = submeter(cliente, autenticado, atividade, COMANDO).json()

    assert segunda["correta"] is True
    assert segunda["xp_ganho"] == 0
    assert segunda["xp_total"] == 10


def test_resposta_aberta_fica_em_analise_e_nao_paga(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    """Dar XP por texto que ninguém leu seria inventar acerto (a IA é a #11)."""
    corpo = submeter(
        cliente,
        autenticado,
        ids(trilha_com_atividades, 1, 3),
        "Uma flag muda o comportamento do comando, como o --version mostrando a versão.",
    ).json()

    assert corpo["em_analise"] is True
    assert corpo["correta"] is False
    assert corpo["xp_ganho"] == 0


def test_resposta_aberta_curta_demais_e_recusada(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    corpo = submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 3), "sei lá").json()

    assert corpo["em_analise"] is False
    assert "caracteres" in corpo["feedback"]


def test_conteudo_vazio_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    resposta = submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), "")

    assert resposta.status_code == 422


def test_nao_da_para_submeter_em_passo_bloqueado(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    resposta = submeter(cliente, autenticado, ids(trilha_com_atividades, 2, 1), "python main.py")

    assert resposta.status_code == 403


# --------------------------------------------------------------------------
# Histórico
# --------------------------------------------------------------------------


def test_cada_tentativa_vira_um_registro(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    atividade = ids(trilha_com_atividades, 1, 1)
    submeter(cliente, autenticado, atividade, "errado")
    submeter(cliente, autenticado, atividade, "errado de novo")
    submeter(cliente, autenticado, atividade, COMANDO)

    historico = cliente.get(
        f"/api/v1/atividades/{atividade}/submissoes", headers=autenticado
    ).json()

    assert [t["tentativa"] for t in historico] == [1, 2, 3]
    assert [t["correta"] for t in historico] == [False, False, True]


def test_historico_guarda_o_tempo_gasto(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    atividade = ids(trilha_com_atividades, 1, 1)
    submeter(cliente, autenticado, atividade, COMANDO)

    historico = cliente.get(
        f"/api/v1/atividades/{atividade}/submissoes", headers=autenticado
    ).json()

    assert historico[0]["tempo_gasto_segundos"] == 12


def test_historico_e_so_do_proprio_aluno(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    atividade = ids(trilha_com_atividades, 1, 1)
    submeter(cliente, autenticado, atividade, COMANDO)

    outro = cliente.post(
        "/api/v1/auth/register",
        json={
            "username": "bia",
            "email": "bia@ufrpe.br",
            "senha": SENHA_VALIDA,
            "aceite_termos": True,
        },
    ).json()

    historico = cliente.get(
        f"/api/v1/atividades/{atividade}/submissoes",
        headers={"Authorization": f"Bearer {outro['access_token']}"},
    ).json()

    assert historico == []


# --------------------------------------------------------------------------
# Concluir o passo
# --------------------------------------------------------------------------


def concluir(cliente: TestClient, headers: dict[str, str], ordem: int):
    return cliente.post(f"/api/v1/trilhas/logica/passos/{ordem}/concluir", headers=headers)


def test_concluir_exige_as_atividades_acertadas(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    resposta = concluir(cliente, autenticado, 1)

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["code"] == "atividades_pendentes"
    assert resposta.json()["erro"]["details"]["pendentes"] == 2


def test_concluir_paga_o_bonus_e_abre_o_proximo(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), COMANDO)
    submeter(
        cliente,
        autenticado,
        ids(trilha_com_atividades, 1, 2),
        "winget install Python.Python.3.14",
    )

    corpo = concluir(cliente, autenticado, 1).json()

    assert corpo["xp_ganho"] == submissoes.XP_POR_PASSO
    # 10 + 15 das atividades, mais o bônus do passo.
    assert corpo["xp_total"] == 25 + submissoes.XP_POR_PASSO
    assert corpo["proximo"] == 2


def test_a_resposta_aberta_nao_trava_o_passo(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    """Ela não tem correção ainda (#11); exigi-la deixaria o aluno preso."""
    submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), COMANDO)
    submeter(
        cliente,
        autenticado,
        ids(trilha_com_atividades, 1, 2),
        "winget install Python.Python.3.14",
    )

    assert concluir(cliente, autenticado, 1).status_code == 200


def test_concluir_duas_vezes_nao_paga_duas_vezes(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), COMANDO)
    submeter(
        cliente,
        autenticado,
        ids(trilha_com_atividades, 1, 2),
        "winget install Python.Python.3.14",
    )
    concluir(cliente, autenticado, 1)

    segunda = concluir(cliente, autenticado, 1).json()

    assert segunda["xp_ganho"] == 0
    assert segunda["xp_total"] == 25 + submissoes.XP_POR_PASSO


def test_passo_concluido_abre_a_atividade_do_seguinte(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), COMANDO)
    submeter(
        cliente,
        autenticado,
        ids(trilha_com_atividades, 1, 2),
        "winget install Python.Python.3.14",
    )
    concluir(cliente, autenticado, 1)

    resposta = cliente.get(
        f"/api/v1/atividades/{ids(trilha_com_atividades, 2, 1)}", headers=autenticado
    )

    assert resposta.status_code == 200


def test_ultimo_passo_nao_tem_proximo(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_atividades: Trilha
) -> None:
    submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), COMANDO)
    submeter(
        cliente,
        autenticado,
        ids(trilha_com_atividades, 1, 2),
        "winget install Python.Python.3.14",
    )
    concluir(cliente, autenticado, 1)
    submeter(cliente, autenticado, ids(trilha_com_atividades, 2, 1), "python main.py")

    assert concluir(cliente, autenticado, 2).json()["proximo"] is None


# --------------------------------------------------------------------------
# XP como fonte da verdade
# --------------------------------------------------------------------------


def test_cada_pagamento_vira_um_evento(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_atividades: Trilha,
) -> None:
    """`xp_eventos` é a fonte da verdade; `usuarios.xp_total` é cache dela."""
    atividade = ids(trilha_com_atividades, 1, 1)
    submeter(cliente, autenticado, atividade, COMANDO)
    submeter(cliente, autenticado, atividade, COMANDO)

    eventos = db.query(XPEvento).filter_by(usuario_id=usuario.id).all()
    assert len(eventos) == 1
    assert (eventos[0].valor, eventos[0].referencia_id) == (10, atividade)


def test_o_progresso_do_aluno_reflete_o_passo_fechado(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_atividades: Trilha,
) -> None:
    submeter(cliente, autenticado, ids(trilha_com_atividades, 1, 1), COMANDO)
    submeter(
        cliente,
        autenticado,
        ids(trilha_com_atividades, 1, 2),
        "winget install Python.Python.3.14",
    )
    concluir(cliente, autenticado, 1)

    concluidos = progresso.concluidos_por_trilha(
        db, usuario_id=usuario.id, trilha_ids=[trilha_com_atividades.id]
    )
    assert concluidos[trilha_com_atividades.id] == 1
