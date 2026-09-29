"""Hash de senha e emissão/validação de JWT.

Senha: `bcrypt` direto, sem `passlib` (ver #87). O bcrypt só considera os
primeiros 72 bytes da senha e, a partir da versão 5, recusa o que passar disso;
o schema de entrada barra antes, com mensagem, em vez de deixar virar 500.

Tokens: dois tipos, com o campo `tipo` separando um do outro para que um refresh
token nunca seja aceito como access token (e vice-versa).

- access: curto (`access_token_ttl`), validado só pela assinatura e pela
  expiração — não consulta o Redis (ver `app/api/deps.py`);
- refresh: longo, com `jti` registrado em `app/services/sessoes.py`. É esse
  registro que permite revogar e rotacionar.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

TipoToken = Literal["access", "refresh"]

# Hash de uma senha qualquer, calculado uma vez. O login compara contra ele
# quando o e-mail não existe, para a resposta levar o mesmo tempo nos dois casos
# e não denunciar quem tem conta.
_HASH_FALSO = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt()).decode()


class TokenInvalido(Exception):
    """Assinatura errada, token vencido, malformado ou do tipo errado."""


@dataclass(frozen=True)
class Token:
    valor: str
    jti: str
    expira_em: datetime


@dataclass(frozen=True)
class Claims:
    usuario_id: int
    jti: str
    expira_em: datetime
    # Só no refresh: se a sessão nasceu com "manter-se conectado" marcado. A
    # rotação carrega isso adiante, senão o refresh encurtaria a sessão.
    estendido: bool = False


def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    """Confere a senha. `senha_hash` nulo (conta só de OAuth) nunca confere."""
    try:
        valida = bcrypt.checkpw(senha.encode(), (senha_hash or _HASH_FALSO).encode())
    except ValueError:
        # Hash corrompido no banco ou senha acima de 72 bytes: não confere.
        return False
    return valida and senha_hash is not None


def emitir(usuario_id: int, tipo: TipoToken, *, ttl: int, estendido: bool = False) -> Token:
    agora = datetime.now(UTC)
    expira_em = agora + timedelta(seconds=ttl)
    jti = uuid.uuid4().hex

    claims: dict[str, object] = {
        "sub": str(usuario_id),
        "tipo": tipo,
        "jti": jti,
        "iat": agora,
        "exp": expira_em,
    }
    if tipo == "refresh":
        claims["estendido"] = estendido

    valor = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algoritmo)
    return Token(valor=valor, jti=jti, expira_em=expira_em)


def decodificar(valor: str, tipo: TipoToken) -> Claims:
    """Valida assinatura, expiração e tipo; levanta `TokenInvalido` se algo falhar.

    `algorithms` é uma lista fechada de propósito: aceitar o algoritmo que vem no
    cabeçalho do token é a brecha clássica do `alg: none`.
    """
    try:
        claims = jwt.decode(valor, settings.jwt_secret, algorithms=[settings.jwt_algoritmo])
    except JWTError as erro:
        raise TokenInvalido(str(erro)) from erro

    if claims.get("tipo") != tipo:
        raise TokenInvalido(f"esperado token {tipo}")

    try:
        return Claims(
            usuario_id=int(claims["sub"]),
            jti=str(claims["jti"]),
            expira_em=datetime.fromtimestamp(claims["exp"], UTC),
            estendido=bool(claims.get("estendido", False)),
        )
    except (KeyError, TypeError, ValueError) as erro:
        raise TokenInvalido("claims ausentes ou malformadas") from erro


def segundos_ate(momento: datetime) -> int:
    """Quanto falta até `momento`, com no mínimo 1 (o SETEX do Redis recusa 0)."""
    return max(int((momento - datetime.now(UTC)).total_seconds()), 1)
