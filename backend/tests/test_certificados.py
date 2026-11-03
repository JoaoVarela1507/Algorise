"""Certificados das trilhas de parceiros: emissão, lista, PDF e validação (#32)."""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Certificado, Modulo, PapelUsuario, Parceiro, Trilha, Usuario
from app.services import certificados


@pytest.fixture
def ufrpe(db: Session) -> Parceiro:
    parceiro = Parceiro(nome="UFRPE")
    db.add(parceiro)
    db.commit()
    return parceiro


@pytest.fixture
def git(db: Session, ufrpe: Parceiro) -> Trilha:
    """Trilha de parceiro de um passo só, sem atividade: fechar o passo conclui a trilha."""
    trilha = Trilha(
        slug="git",
        nome="Git",
        disciplina="Ferramentas",
        periodo=1,
        publicada=True,
        parceiro_id=ufrpe.id,
        carga_horaria=20,
    )
    trilha.modulos = [Modulo(ordem=1, titulo="Clone")]
    db.add(trilha)
    db.commit()
    return trilha


def concluir(cliente: TestClient, headers: dict[str, str], slug: str = "git") -> None:
    resposta = cliente.post(f"/api/v1/trilhas/{slug}/passos/1/concluir", headers=headers)
    assert resposta.status_code == 200, resposta.text


def lista(cliente: TestClient, headers: dict[str, str]) -> list[dict]:
    resposta = cliente.get("/api/v1/certificados", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --- emissão ------------------------------------------------------------------------------


def test_concluir_a_trilha_de_parceiro_emite_o_certificado(
    cliente: TestClient, autenticado: dict[str, str], git: Trilha, usuario: Usuario
) -> None:
    """O critério da #32."""
    [antes] = lista(cliente, autenticado)
    item = antes["itens"][0]
    assert (item["estado"], item["concluidos"], item["certificado_id"]) == ("bloqueado", 0, None)

    concluir(cliente, autenticado)

    [periodo] = lista(cliente, autenticado)
    [item] = periodo["itens"]
    assert (periodo["periodo"], item["estado"], item["parceiro"], item["carga_horaria"]) == (
        1,
        "liberado",
        "UFRPE",
        20,
    )
    detalhe = cliente.get(
        f"/api/v1/certificados/{item['certificado_id']}", headers=autenticado
    ).json()
    assert (detalhe["nome_aluno"], detalhe["nome_trilha"], detalhe["disciplina"]) == (
        usuario.nome_exibicao,
        "Git",
        "Ferramentas",
    )
    assert detalhe["codigo"].startswith("ALG-")


def test_trilha_sem_parceiro_nao_emite_nem_aparece(
    cliente: TestClient, autenticado: dict[str, str], db: Session
) -> None:
    trilha = Trilha(slug="livre", nome="Livre", disciplina="X", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Um")]
    db.add(trilha)
    db.commit()

    concluir(cliente, autenticado, "livre")

    assert lista(cliente, autenticado) == []
    assert db.query(Certificado).count() == 0


def test_emitir_de_novo_devolve_o_mesmo(
    cliente: TestClient, autenticado: dict[str, str], git: Trilha, db: Session, usuario: Usuario
) -> None:
    concluir(cliente, autenticado)
    concluir(cliente, autenticado)

    assert db.query(Certificado).count() == 1
    db.expire_all()
    assert certificados.emitir_se_concluiu(
        db, db.get(Usuario, usuario.id), db.get(Trilha, git.id)
    ).id


def test_emissao_vai_para_a_auditoria(
    cliente: TestClient, autenticado: dict[str, str], git: Trilha, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.auditoria"):
        concluir(cliente, autenticado)

    assert [r.evento for r in caplog.records if r.name == "app.auditoria"] == [
        "certificado_emitido"
    ]


# --- PDF ----------------------------------------------------------------------------------


def test_pdf_so_para_o_dono(
    cliente: TestClient, autenticado: dict[str, str], git: Trilha, db: Session
) -> None:
    concluir(cliente, autenticado)
    certificado = db.query(Certificado).one()

    meu = cliente.get(f"/api/v1/certificados/{certificado.id}/download", headers=autenticado)

    assert meu.status_code == 200
    assert meu.headers["content-type"] == "application/pdf"
    assert meu.content.startswith(b"%PDF")
    assert certificado.codigo in meu.headers["content-disposition"]

    outro = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(outro)
    db.commit()
    certificado.usuario_id = outro.id
    db.commit()
    alheio = cliente.get(f"/api/v1/certificados/{certificado.id}/download", headers=autenticado)
    inexistente = cliente.get("/api/v1/certificados/999/download", headers=autenticado)

    assert (alheio.status_code, inexistente.status_code) == (404, 404)


def test_pdf_aceita_acento_e_sobrevive_a_emoji() -> None:
    certificado = Certificado(
        codigo="ALG-2345-6789",
        nome_aluno="João Conceição 🚀",
        nome_trilha="Introdução à Programação",
        disciplina="Lógica",
        carga_horaria=60,
        parceiro="UFRPE",
    )

    assert certificados.pdf(certificado).startswith(b"%PDF")


# --- validação pública --------------------------------------------------------------------


def test_validacao_publica_mostra_o_que_o_certificado_diz(
    cliente: TestClient, autenticado: dict[str, str], git: Trilha, db: Session
) -> None:
    concluir(cliente, autenticado)
    certificado = db.query(Certificado).one()
    # Mudanças depois da emissão não alteram o certificado.
    git.nome = "Git avançado"
    db.commit()

    resposta = cliente.get(f"/api/v1/certificados/validar/{certificado.codigo.lower()}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["nome_trilha"], corpo["parceiro"], corpo["carga_horaria"]) == ("Git", "UFRPE", 20)
    assert "usuario_id" not in corpo and "email" not in corpo


def test_codigo_que_nao_existe_responde_404(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/certificados/validar/ALG-0000-0000")

    assert (resposta.status_code, resposta.json()["erro"]["code"]) == (404, "certificado_invalido")


def test_codigo_nao_tem_letra_que_confunde(db: Session) -> None:
    codigo = certificados._codigo_livre(db)

    assert len(codigo) == len("ALG-XXXX-XXXX")
    assert not set(codigo[4:]) & set("01ILO")


# --- parceiros na API administrativa ------------------------------------------------------


def test_admin_cadastra_parceiro_e_liga_a_trilha(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, git: Trilha
) -> None:
    usuario.papel = PapelUsuario.admin
    db.merge(usuario)
    db.commit()

    parceiro = cliente.post(
        "/api/v1/admin/parceiros", headers=autenticado, json={"nome": "IFPE"}
    ).json()
    ligada = cliente.patch(
        f"/api/v1/admin/trilhas/{git.id}",
        headers=autenticado,
        json={"parceiro_id": parceiro["id"], "carga_horaria": 40},
    )
    inexistente = cliente.patch(
        f"/api/v1/admin/trilhas/{git.id}", headers=autenticado, json={"parceiro_id": 999}
    )

    assert (ligada.json()["parceiro_id"], ligada.json()["carga_horaria"]) == (parceiro["id"], 40)
    assert (inexistente.status_code, inexistente.json()["erro"]["code"]) == (
        404,
        "parceiro_nao_encontrado",
    )


def test_cors_expoe_o_nome_do_arquivo_do_pdf(cliente) -> None:
    from app.core.config import settings

    resposta = cliente.get("/health", headers={"Origin": settings.frontend_origin})

    assert resposta.headers["access-control-expose-headers"] == "Content-Disposition"
