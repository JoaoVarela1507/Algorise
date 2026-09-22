"""Hash de senha e tokens JWT.

Duas peças sem dependência de banco nem de rede, para poderem ser testadas
sozinhas e reaproveitadas pelo login por senha e pelo login social.

Sobre o hash: a issue pedia `passlib[bcrypt]`, mas o passlib é de 2020 e não
funciona com o bcrypt 5 (nem lê a versão do bcrypt 4 sem imprimir traceback). Usa
a biblioteca `bcrypt` direto, que é o que o passlib chamaria no fim das contas.

Sobre os tokens: o access é curto e vale sozinho — quem o valida não consulta o
Redis, senão o Redis fora derrubaria toda a API autenticada. O refresh é longo,
carrega um `jti`, e é esse `jti` que o Redis registra e revoga
(`app/services/sessoes.py`).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Limite do algoritmo, não escolha nossa: o bcrypt ignora o que passar disso e
# rejeitar é melhor do que truncar sem avisar.
MAXIMO_BYTES_SENHA = 72

TipoToken = Literal["access", "refresh"]


class TokenInvalido(Exception):
    """Token expirado, adulterado, do tipo errado ou sem os campos esperados."""


def gerar_hash_senha(senha: str) -> str:
    bytes_senha = senha.encode("utf-8")
    if len(bytes_senha) > MAXIMO_BYTES_SENHA:
        raise ValueError(f"A senha passa de {MAXIMO_BYTES_SENHA} bytes")

    return bcrypt.hashpw(bytes_senha, bcrypt.gensalt()).decode("utf-8")


def conferir_senha(senha: str, hash_armazenado: str | None) -> bool:
    """Compara senha e hash.

    `hash_armazenado` vem nulo para conta criada por GitHub ou Google. Mesmo
    nesse caso o hash falso é verificado, para o tempo de resposta não denunciar
    que a conta existe e não tem senha.
    """
    referencia = hash_armazenado or _HASH_FALSO
    try:
        confere = bcrypt.checkpw(senha.encode("utf-8"), referencia.encode("utf-8"))
    except ValueError:
        # Hash malformado no banco: trata como senha errada, não como erro 500.
        return False

    return confere and hash_armazenado is not None


def criar_access_token(usuario_id: int) -> str:
    return _criar_token(usuario_id, tipo="access", validade=settings.access_token_ttl)


def criar_refresh_token(usuario_id: int, *, ttl: int) -> tuple[str, str]:
    """Devolve o token e o `jti` dele, que é o identificador da sessão."""
    jti = uuid.uuid4().hex
    return _criar_token(usuario_id, tipo="refresh", validade=ttl, jti=jti), jti


def decodificar(token: str, *, tipo: TipoToken) -> dict[str, Any]:
    """Valida assinatura, prazo e tipo, e devolve o conteúdo.

    O tipo é conferido aqui de propósito: sem isso, um refresh token serviria
    como access token e a sessão nunca poderia ser revogada de verdade.
    """
    try:
        conteudo = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algoritmo])
    except JWTError as erro:
        raise TokenInvalido(str(erro)) from erro

    if conteudo.get("tipo") != tipo:
        raise TokenInvalido(f"Esperava um token do tipo {tipo}")
    if not conteudo.get("sub"):
        raise TokenInvalido("Token sem dono")

    return conteudo


def _criar_token(usuario_id: int, *, tipo: TipoToken, validade: int, jti: str | None = None) -> str:
    agora = datetime.now(UTC)
    conteudo: dict[str, Any] = {
        # `sub` é string por exigência do JWT, mesmo o id sendo inteiro.
        "sub": str(usuario_id),
        "tipo": tipo,
        "iat": agora,
        "exp": agora + timedelta(seconds=validade),
    }
    if jti is not None:
        conteudo["jti"] = jti

    return jwt.encode(conteudo, settings.jwt_secret, algorithm=settings.jwt_algoritmo)


# Hash de uma senha aleatória, gerado uma vez no import: serve só para gastar o
# mesmo tempo de CPU quando a conta não tem senha (ver `conferir_senha`).
_HASH_FALSO = bcrypt.hashpw(uuid.uuid4().hex.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
