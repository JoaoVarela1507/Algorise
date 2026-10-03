"""Dependências compartilhadas pelas rotas."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.seguranca import TokenInvalido, decodificar
from app.models import Usuario

# `auto_error=False` para a resposta sem header sair com o mesmo 401 e o mesmo
# corpo de um token inválido, em vez do 403 que o FastAPI devolveria.
esquema = HTTPBearer(auto_error=False, description="Access token do /auth/login")

NAO_AUTORIZADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais inválidas ou expiradas",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema)] = None,
    db: Session = Depends(get_db),
) -> Usuario:
    """O aluno dono do access token, ou 401.

    Valida assinatura, prazo e tipo do token — e só. Não pergunta ao Redis se a
    sessão continua aberta: se perguntasse, o Redis fora derrubaria toda a API
    autenticada, o contrário do que a #12 pede. O preço é que o logout leva até
    o prazo do access token (15 minutos) para valer; o refresh, esse sim, é
    revogado na hora.
    """
    if credenciais is None:
        raise NAO_AUTORIZADO

    try:
        conteudo = decodificar(credenciais.credentials, tipo="access")
    except TokenInvalido as erro:
        raise NAO_AUTORIZADO from erro

    usuario = db.get(Usuario, int(conteudo["sub"]))
    if usuario is None or usuario.exclusao_agendada_para is not None:
        # Token válido de uma conta que não existe mais, ou que pediu exclusão
        # (#40): o access emitido antes do pedido não pode seguir valendo pelos
        # minutos que ainda tem.
        raise NAO_AUTORIZADO

    return usuario


UsuarioAtual = Annotated[Usuario, Depends(get_current_user)]


def get_usuario_opcional(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema)] = None,
    db: Session = Depends(get_db),
) -> Usuario | None:
    """O aluno, quando há token válido; None quando não há.

    Para rota que serve visitante e aluno pela mesma porta — o catálogo de
    trilhas mostra o mesmo conteúdo para os dois, e só acrescenta o progresso
    para quem está logado. Token inválido aqui é tratado como visitante, e não
    como erro: recusar a página inteira por causa de um token vencido esconderia
    conteúdo público.
    """
    if credenciais is None:
        return None

    try:
        return get_current_user(credenciais, db)
    except HTTPException:
        return None


UsuarioOpcional = Annotated[Usuario | None, Depends(get_usuario_opcional)]
