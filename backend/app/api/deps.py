"""Dependências compartilhadas pelas rotas."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import seguranca
from app.core.database import get_db
from app.models import Usuario

# `auto_error=False` para devolver 401 (o FastAPI devolveria 403 sem o cabeçalho)
# e com o `WWW-Authenticate` que a RFC 6750 pede.
_bearer = HTTPBearer(auto_error=False)

_NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão inválida ou expirada.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Aluno dono do access token. 401 se o token faltar, vencer ou for adulterado.

    Valida assinatura e expiração, mas **não** consulta o Redis (ver #89): se
    consultasse, o Redis fora derrubaria toda a API autenticada. O logout mata o
    refresh na hora, e o access token morre sozinho no prazo curto dele.
    """
    if credenciais is None:
        raise _NAO_AUTENTICADO

    try:
        claims = seguranca.decodificar(credenciais.credentials, "access")
    except seguranca.TokenInvalido as erro:
        raise _NAO_AUTENTICADO from erro

    usuario = db.get(Usuario, claims.usuario_id)
    if usuario is None:
        # Conta apagada depois de o token ser emitido.
        raise _NAO_AUTENTICADO
    return usuario


# Açúcar para as rotas: `usuario: UsuarioAtual`.
UsuarioAtual = Annotated[Usuario, Depends(get_current_user)]
