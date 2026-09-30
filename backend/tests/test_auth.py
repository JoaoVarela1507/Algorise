"""Testes da autenticação.

A ordem aqui segue os bugs do #106: cada um deles virou um teste, porque foram
sete correções numa área que não tinha suíte nenhuma. Os testes marcados com
`#106` existem para reprovar o PR se o comportamento voltar.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core import seguranca
from app.core.config import settings
from app.models import Usuario
from app.services import auth as servico
from app.services import sessoes
from tests.conftest import SENHA_VALIDA

CADASTRO = {
    "username": "bia",
    "email": "bia@ufrpe.br",
    "senha": SENHA_VALIDA,
    "aceite_termos": True,
}


def registrar(cliente: TestClient, **mudancas: object):
    return cliente.post("/api/v1/auth/register", json=CADASTRO | mudancas)


# --------------------------------------------------------------------------
# Cadastro
# --------------------------------------------------------------------------


def test_cadastro_devolve_sessao(cliente: TestClient) -> None:
    resposta = registrar(cliente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["access_token"] and corpo["refresh_token"]
    assert corpo["usuario"]["username"] == "bia"
    assert corpo["expira_em"] == settings.access_token_ttl


def test_cadastro_normaliza_o_email(cliente: TestClient) -> None:
    resposta = registrar(cliente, email="BIA@UFRPE.br")

    assert resposta.json()["usuario"]["email"] == "bia@ufrpe.br"


def test_cadastro_sem_nome_de_exibicao_usa_o_username(cliente: TestClient) -> None:
    """#106: o campo era obrigatório e o formulário da tela 6 não o tem."""
    resposta = registrar(cliente)

    assert resposta.status_code == 201
    assert resposta.json()["usuario"]["nome_exibicao"] == "bia"


def test_cadastro_com_email_repetido_devolve_409(cliente: TestClient) -> None:
    registrar(cliente)

    resposta = registrar(cliente, username="outra")

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["code"] == "email_em_uso"
    assert resposta.json()["erro"]["details"]["campo"] == "email"


def test_cadastro_com_username_repetido_devolve_409(cliente: TestClient) -> None:
    """#106: antes o username era trocado em silêncio por `bia2`."""
    registrar(cliente)

    resposta = registrar(cliente, email="outra@ufrpe.br")

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["code"] == "username_em_uso"


def test_username_repetido_ignora_maiusculas(cliente: TestClient) -> None:
    registrar(cliente)

    resposta = registrar(cliente, email="outra@ufrpe.br", username="BIA")

    assert resposta.status_code == 409


def test_cadastro_sem_aceite_dos_termos_e_recusado(cliente: TestClient) -> None:
    resposta = registrar(cliente, aceite_termos=False)

    assert resposta.status_code == 422


@pytest.mark.parametrize(
    ("senha", "motivo"),
    [
        ("curta", "menos que o mínimo"),
        ("senha123", "senha comum"),
        ("12345678", "sequência"),
        ("aaaaaaaa", "repete o mesmo caractere"),
    ],
)
def test_cadastro_recusa_senha_fraca(cliente: TestClient, senha: str, motivo: str) -> None:
    resposta = registrar(cliente, senha=senha)

    assert resposta.status_code == 422, f"deveria recusar por {motivo}"


def test_cadastro_recusa_senha_que_contem_o_username(cliente: TestClient) -> None:
    resposta = registrar(cliente, username="mariana", senha="mariana-2026")

    assert resposta.status_code == 422


def test_username_curto_nao_bloqueia_a_senha(cliente: TestClient) -> None:
    """Trecho com menos de quatro letras não conta: barrar "bia" dentro da senha
    de quem se chama Bia recusaria senhas boas à toa."""
    resposta = registrar(cliente, username="bia", senha="bia-Trilha-2026")

    assert resposta.status_code == 201


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------


def test_login_devolve_sessao(cliente: TestClient, usuario: Usuario) -> None:
    resposta = cliente.post(
        "/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA_VALIDA}
    )

    assert resposta.status_code == 200
    assert resposta.json()["usuario"]["username"] == usuario.username


def test_senha_errada_e_conta_inexistente_respondem_igual(
    cliente: TestClient, usuario: Usuario
) -> None:
    """A resposta não pode servir para descobrir quem tem cadastro."""
    errada = cliente.post(
        "/api/v1/auth/login", json={"email": usuario.email, "senha": "Outra-Senha-2026"}
    )
    inexistente = cliente.post(
        "/api/v1/auth/login", json={"email": "ninguem@ufrpe.br", "senha": "Outra-Senha-2026"}
    )

    assert errada.status_code == inexistente.status_code == 401
    # O `request_id` muda a cada requisição; o resto tem de ser idêntico.
    assert errada.json()["erro"]["code"] == inexistente.json()["erro"]["code"]
    assert errada.json()["erro"]["message"] == inexistente.json()["erro"]["message"]


def test_login_bloqueia_apos_tentativas_erradas(cliente: TestClient, usuario: Usuario) -> None:
    for _ in range(settings.rate_limit_auth_requisicoes + 1):
        resposta = cliente.post(
            "/api/v1/auth/login", json={"email": usuario.email, "senha": "Errada-Demais-1"}
        )
        if resposta.status_code == 429:
            break

    assert resposta.status_code == 429
    assert resposta.headers["Retry-After"].isdigit()


def test_manter_conectado_alonga_o_refresh(cliente: TestClient, usuario: Usuario) -> None:
    def prazo(lembrar: bool) -> int:
        resposta = cliente.post(
            "/api/v1/auth/login",
            json={"email": usuario.email, "senha": SENHA_VALIDA, "lembrar": lembrar},
        )
        conteudo = seguranca.decodificar(resposta.json()["refresh_token"], tipo="refresh")
        return conteudo["exp"] - conteudo["iat"]

    assert prazo(lembrar=False) == settings.refresh_token_ttl
    assert prazo(lembrar=True) == settings.refresh_token_ttl_lembrar


def test_login_sem_redis_devolve_503(
    cliente: TestClient, usuario: Usuario, redis_fora: None
) -> None:
    """#106: era 500. A senha estava certa — só a sessão não pôde ser gravada."""
    resposta = cliente.post(
        "/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA_VALIDA}
    )

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["code"] == "sessao_indisponivel"


# --------------------------------------------------------------------------
# Sessão
# --------------------------------------------------------------------------


def test_rota_protegida_aceita_o_token(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    resposta = cliente.get("/api/v1/auth/eu", headers=autenticado)

    assert resposta.status_code == 200
    assert resposta.json()["username"] == usuario.username


def test_rota_protegida_sem_token_devolve_401(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/auth/eu")

    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"] == "Bearer"


def test_refresh_nao_serve_como_access(cliente: TestClient, sessao_aberta: dict[str, str]) -> None:
    """Se servisse, revogar a sessão não adiantaria nada."""
    resposta = cliente.get(
        "/api/v1/auth/eu",
        headers={"Authorization": f"Bearer {sessao_aberta['refresh_token']}"},
    )

    assert resposta.status_code == 401


def test_token_vencido_devolve_401(cliente: TestClient, usuario: Usuario) -> None:
    vencido = jwt.encode(
        {
            "sub": str(usuario.id),
            "tipo": "access",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algoritmo,
    )

    resposta = cliente.get("/api/v1/auth/eu", headers={"Authorization": f"Bearer {vencido}"})

    assert resposta.status_code == 401


def test_token_adulterado_devolve_401(cliente: TestClient, sessao_aberta: dict[str, str]) -> None:
    adulterado = sessao_aberta["access_token"][:-2] + "xx"

    resposta = cliente.get("/api/v1/auth/eu", headers={"Authorization": f"Bearer {adulterado}"})

    assert resposta.status_code == 401


def test_refresh_rotaciona_o_token(cliente: TestClient, sessao_aberta: dict[str, str]) -> None:
    resposta = cliente.post(
        "/api/v1/auth/refresh", json={"refresh_token": sessao_aberta["refresh_token"]}
    )

    assert resposta.status_code == 200
    assert resposta.json()["refresh_token"] != sessao_aberta["refresh_token"]


def test_refresh_reusado_devolve_401(cliente: TestClient, sessao_aberta: dict[str, str]) -> None:
    antigo = sessao_aberta["refresh_token"]
    cliente.post("/api/v1/auth/refresh", json={"refresh_token": antigo})

    resposta = cliente.post("/api/v1/auth/refresh", json={"refresh_token": antigo})

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["code"] == "sessao_expirada"


def test_refresh_simultaneo_rende_uma_sessao_so(
    cliente: TestClient, sessao_aberta: dict[str, str]
) -> None:
    """#106: o mesmo token rendia até sete pares, porque ler e revogar eram
    operações separadas. Aqui as oito tentativas usam o mesmo token."""
    respostas = [
        cliente.post("/api/v1/auth/refresh", json={"refresh_token": sessao_aberta["refresh_token"]})
        for _ in range(8)
    ]

    assert sum(r.status_code == 200 for r in respostas) == 1


def test_manter_conectado_sobrevive_ao_refresh(cliente: TestClient, usuario: Usuario) -> None:
    """#106: a sessão de 30 dias virava de 7 na primeira renovação."""
    entrada = cliente.post(
        "/api/v1/auth/login",
        json={"email": usuario.email, "senha": SENHA_VALIDA, "lembrar": True},
    ).json()

    renovada = cliente.post(
        "/api/v1/auth/refresh", json={"refresh_token": entrada["refresh_token"]}
    ).json()

    conteudo = seguranca.decodificar(renovada["refresh_token"], tipo="refresh")
    assert conteudo["exp"] - conteudo["iat"] == settings.refresh_token_ttl_lembrar


def test_logout_derruba_a_sessao(cliente: TestClient, sessao_aberta: dict[str, str]) -> None:
    saida = cliente.post(
        "/api/v1/auth/logout", json={"refresh_token": sessao_aberta["refresh_token"]}
    )

    assert saida.status_code == 204
    depois = cliente.post(
        "/api/v1/auth/refresh", json={"refresh_token": sessao_aberta["refresh_token"]}
    )
    assert depois.status_code == 401


def test_logout_de_token_invalido_tambem_devolve_204(cliente: TestClient) -> None:
    """O fim pretendido — sessão encerrada — já está cumprido."""
    resposta = cliente.post("/api/v1/auth/logout", json={"refresh_token": "qualquer"})

    assert resposta.status_code == 204


def test_rota_protegida_funciona_com_redis_fora(
    cliente: TestClient, autenticado: dict[str, str], redis_fora: None
) -> None:
    """O access token não é consultado no Redis de propósito: se fosse, uma
    queda do cache derrubaria toda a API autenticada (#12)."""
    assert cliente.get("/api/v1/auth/eu", headers=autenticado).status_code == 200


# --------------------------------------------------------------------------
# Recuperação de senha
# --------------------------------------------------------------------------


def test_esqueci_senha_responde_igual_para_email_desconhecido(
    cliente: TestClient, usuario: Usuario
) -> None:
    conhecido = cliente.post("/api/v1/auth/esqueci-senha", json={"email": usuario.email})
    desconhecido = cliente.post("/api/v1/auth/esqueci-senha", json={"email": "ninguem@ufrpe.br"})

    assert conhecido.status_code == desconhecido.status_code == 202
    assert conhecido.json() == desconhecido.json()


def test_redefinir_senha_troca_e_derruba_as_sessoes(
    cliente: TestClient, db: Session, usuario: Usuario, sessao_aberta: dict[str, str]
) -> None:
    token = servico.criar_token_de_recuperacao(db, usuario.email)
    nova = "Outra-Trilha-2027"

    troca = cliente.post("/api/v1/auth/redefinir-senha", json={"token": token, "senha": nova})

    assert troca.status_code == 204
    assert (
        cliente.post("/api/v1/auth/login", json={"email": usuario.email, "senha": nova}).status_code
        == 200
    )
    assert (
        cliente.post(
            "/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA_VALIDA}
        ).status_code
        == 401
    )
    assert (
        cliente.post(
            "/api/v1/auth/refresh", json={"refresh_token": sessao_aberta["refresh_token"]}
        ).status_code
        == 401
    )


def test_token_de_recuperacao_vale_uma_vez_so(
    cliente: TestClient, db: Session, usuario: Usuario
) -> None:
    token = servico.criar_token_de_recuperacao(db, usuario.email)
    cliente.post("/api/v1/auth/redefinir-senha", json={"token": token, "senha": "Uma-Senha-2027"})

    segunda = cliente.post(
        "/api/v1/auth/redefinir-senha", json={"token": token, "senha": "Mais-Uma-2027"}
    )

    assert segunda.status_code == 400
    assert segunda.json()["erro"]["code"] == "link_invalido"


def test_token_de_recuperacao_nao_fica_em_claro_no_redis(
    db: Session, usuario: Usuario, redis_falso
) -> None:
    """Um dump do Redis não pode virar um passe para trocar senha."""
    token = servico.criar_token_de_recuperacao(db, usuario.email)

    assert token is not None
    assert all(token not in chave for chave in redis_falso.keys("*"))


# --------------------------------------------------------------------------
# Sessões no Redis
# --------------------------------------------------------------------------


def test_revogar_sessoes_do_usuario_derruba_todas(redis_falso) -> None:
    sessoes.registrar_refresh_token("jti-1", 42, ttl=60)
    sessoes.registrar_refresh_token("jti-2", 42, ttl=60)

    assert sessoes.revogar_sessoes_do_usuario(42) == 2
    assert sessoes.usuario_do_refresh_token("jti-1") is None
    assert sessoes.esta_revogado("jti-2")


def test_sessao_falha_fechado_sem_redis(redis_fora: None) -> None:
    """Aqui o Redis é fonte da verdade, não cache: sem ele, não se aceita o token."""
    assert sessoes.usuario_do_refresh_token("qualquer") is None
    assert sessoes.esta_revogado("qualquer") is True
    assert sessoes.registrar_refresh_token("jti", 1) is False
