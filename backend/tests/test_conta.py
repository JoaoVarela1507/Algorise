"""Testes do perfil e dos direitos do titular (#40).

Exportar e excluir os próprios dados é obrigação legal e mexe em dado que não
volta — é a última área do backend onde vale confiar em teste manual.
"""

from datetime import UTC, datetime, timedelta

import fakeredis
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Usuario
from app.services import conta
from tests.conftest import SENHA_VALIDA

EXCLUSAO = {"confirmacao": "EXCLUIR", "senha": SENHA_VALIDA}


# --------------------------------------------------------------------------
# Perfil
# --------------------------------------------------------------------------


def test_perfil_traz_o_que_as_telas_privadas_mostram(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    corpo = cliente.get("/api/v1/usuarios/me", headers=autenticado).json()

    assert corpo["username"] == usuario.username
    assert corpo["tem_senha"] is True
    assert {"xp_total", "streak_dias", "nivel_experiencia", "tipo_trilha"} <= set(corpo)


def test_perfil_exige_autenticacao(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/usuarios/me").status_code == 401


def test_patch_altera_so_o_que_foi_enviado(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    antes = cliente.get("/api/v1/usuarios/me", headers=autenticado).json()

    depois = cliente.patch("/api/v1/usuarios/me", headers=autenticado, json={"periodo": 3}).json()

    assert depois["periodo"] == 3
    assert depois["nome_exibicao"] == antes["nome_exibicao"]


def test_onboarding_grava_instituicao_e_curso(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    corpo = cliente.patch(
        "/api/v1/usuarios/me",
        headers=autenticado,
        json={"instituicao": "UFRPE", "curso": "Ciência da Computação", "periodo": 1},
    ).json()

    assert corpo["instituicao"] == "UFRPE"
    assert corpo["curso"] == "Ciência da Computação"


def test_curso_sem_instituicao_e_recusado(cliente: TestClient, autenticado: dict[str, str]) -> None:
    resposta = cliente.patch(
        "/api/v1/usuarios/me", headers=autenticado, json={"curso": "Sistemas de Informação"}
    )

    assert resposta.status_code == 422


# --------------------------------------------------------------------------
# Exportar os dados (LGPD)
# --------------------------------------------------------------------------


def test_exportar_dados_baixa_como_arquivo(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    resposta = cliente.get("/api/v1/usuarios/me/dados", headers=autenticado)

    assert resposta.status_code == 200
    assert "attachment" in resposta.headers["Content-Disposition"]
    # Dado pessoal: nem navegador nem proxy no caminho guardam cópia.
    assert resposta.headers["Cache-Control"] == "no-store"


def test_exportacao_nao_leva_o_hash_da_senha(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    resposta = cliente.get("/api/v1/usuarios/me/dados", headers=autenticado)

    assert usuario.email in resposta.text
    assert "senha_hash" not in resposta.text
    assert (usuario.senha_hash or "impossível") not in resposta.text


# --------------------------------------------------------------------------
# Excluir a conta (LGPD)
# --------------------------------------------------------------------------


def test_exclusao_agenda_e_derruba_as_sessoes(
    cliente: TestClient,
    autenticado: dict[str, str],
    sessao_aberta: dict[str, str],
    usuario: Usuario,
) -> None:
    resposta = cliente.request("DELETE", "/api/v1/usuarios/me", headers=autenticado, json=EXCLUSAO)

    assert resposta.status_code == 202
    assert resposta.json()["exclusao_agendada_para"]
    assert (
        cliente.post(
            "/api/v1/auth/refresh", json={"refresh_token": sessao_aberta["refresh_token"]}
        ).status_code
        == 401
    )


def test_exclusao_sem_a_palavra_certa_e_recusada(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    """A confirmação explícita é o que separa isso de um clique sem querer."""
    resposta = cliente.request(
        "DELETE",
        "/api/v1/usuarios/me",
        headers=autenticado,
        json={"confirmacao": "sim", "senha": SENHA_VALIDA},
    )

    assert resposta.status_code == 403


def test_exclusao_com_senha_errada_e_recusada(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    """Quem pegou um access token não apaga a conta alheia só com ele."""
    resposta = cliente.request(
        "DELETE",
        "/api/v1/usuarios/me",
        headers=autenticado,
        json={"confirmacao": "EXCLUIR", "senha": "Outra-Senha-2026"},
    )

    assert resposta.status_code == 403


def test_entrar_de_novo_cancela_a_exclusao(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    cliente.request("DELETE", "/api/v1/usuarios/me", headers=autenticado, json=EXCLUSAO)

    entrada = cliente.post(
        "/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA_VALIDA}
    )

    assert entrada.status_code == 200
    assert entrada.json()["aviso"]


def test_expurgo_apaga_so_as_vencidas(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    conta.agendar_exclusao(db, usuario, confirmacao="EXCLUIR", senha=SENHA_VALIDA)

    # Ainda dentro do prazo: o expurgo não pode tocar nela.
    assert conta.expurgar_vencidas(db) == 0

    vencido = datetime.now(UTC) + timedelta(days=settings.prazo_exclusao_dias + 1)
    assert conta.expurgar_vencidas(db, agora=vencido) == 1
    assert db.get(Usuario, usuario.id) is None
