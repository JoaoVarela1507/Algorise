"""Rotas de autenticação: registro, login, sessão e recuperação de senha.

O login social tem arquivo próprio (`oauth.py`), porque ali entra redirecionamento
e cliente HTTP externo.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import (
    EsqueciSenha,
    Login,
    RedefinirSenha,
    Registro,
    Renovacao,
    Sessao,
    UsuarioAutenticado,
)
from app.services import auth as servico

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    # Mesma mensagem para e-mail sem conta e senha errada: a resposta não pode
    # servir para descobrir quem tem cadastro.
    detail="E-mail ou senha incorretos",
)


@router.post("/register", response_model=Sessao, status_code=status.HTTP_201_CREATED)
def registrar(dados: Registro, db: Session = Depends(get_db)) -> Sessao:
    try:
        usuario = servico.registrar(
            db,
            email=dados.email,
            senha=dados.senha,
            nome_exibicao=dados.nome_exibicao,
            username=dados.username,
        )
    except servico.EmailEmUso as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com esse e-mail"
        ) from erro

    return servico.abrir_sessao(usuario)


@router.post("/login", response_model=Sessao)
def entrar(dados: Login, db: Session = Depends(get_db)) -> Sessao:
    try:
        usuario = servico.autenticar(db, email=dados.email, senha=dados.senha)
    except servico.CredenciaisInvalidas as erro:
        raise CREDENCIAIS_INVALIDAS from erro

    return servico.abrir_sessao(usuario, lembrar=dados.lembrar)


@router.post("/refresh", response_model=Sessao)
def renovar(dados: Renovacao, db: Session = Depends(get_db)) -> Sessao:
    try:
        return servico.renovar_sessao(db, dados.refresh_token)
    except servico.SessaoExpirada as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada, entre de novo"
        ) from erro


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def sair(dados: Renovacao) -> Response:
    """Encerra a sessão. Responde 204 mesmo com token já inválido: o fim é o mesmo."""
    servico.encerrar_sessao(dados.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/eu", response_model=UsuarioAutenticado)
def eu(usuario: UsuarioAtual) -> UsuarioAutenticado:
    """Rota protegida de referência: é o que o frontend chama ao abrir o app."""
    return UsuarioAutenticado.model_validate(usuario)


@router.post("/esqueci-senha", status_code=status.HTTP_202_ACCEPTED)
def esqueci_senha(dados: EsqueciSenha, db: Session = Depends(get_db)) -> dict[str, str]:
    """Começa a recuperação. Sempre 202, tenha o e-mail conta ou não."""
    token = servico.criar_token_de_recuperacao(db, dados.email)

    if token is not None:
        # Enquanto não existe serviço de e-mail, o link vai para o log. Trocar
        # isso pelo envio é a única mudança que essa rota ainda precisa.
        logger.info(
            "Link de recuperação de senha: %s/redefinir-senha?token=%s",
            settings.frontend_origin,
            token,
        )

    return {"detail": "Se houver conta com esse e-mail, o link de recuperação foi enviado"}


@router.post("/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(dados: RedefinirSenha, db: Session = Depends(get_db)) -> Response:
    try:
        servico.redefinir_senha(db, token=dados.token, senha=dados.senha)
    except servico.TokenDeSenhaInvalido as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de recuperação inválido ou expirado",
        ) from erro

    return Response(status_code=status.HTTP_204_NO_CONTENT)
