"""Rotas de autenticação: registro, login, sessão e recuperação de senha.

O login social tem arquivo próprio (`oauth.py`), porque ali entra redirecionamento
e cliente HTTP externo.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limite_por_ip
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
from app.services import conta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    # Mesma mensagem para e-mail sem conta e senha errada: a resposta não pode
    # servir para descobrir quem tem cadastro.
    detail="E-mail ou senha incorretos",
)

SESSAO_INDISPONIVEL = HTTPException(
    # O Redis não gravou a sessão. 503 e não 401: a senha estava certa, e o
    # aluno só precisa tentar de novo.
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Não foi possível abrir a sessão agora, tente de novo em instantes",
)

AVISO_EXCLUSAO_CANCELADA = "A exclusão da sua conta foi cancelada porque você entrou de novo."


def _limite(nome: str):
    """Rate limit por IP (#40), um contador por rota."""
    return limite_por_ip(
        nome,
        limite=settings.rate_limit_auth_requisicoes,
        janela=settings.rate_limit_auth_janela,
    )


def _senha_fraca(erro: servico.SenhaFraca) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erro))


@router.post(
    "/register",
    response_model=Sessao,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_limite("register")],
)
def registrar(dados: Registro, request: Request, db: Session = Depends(get_db)) -> Sessao:
    try:
        usuario = servico.registrar(
            db,
            email=dados.email,
            senha=dados.senha,
            nome_exibicao=dados.nome_exibicao,
            username=dados.username,
            ip=request.client.host if request.client else None,
        )
    except servico.SenhaFraca as erro:
        raise _senha_fraca(erro) from erro
    except servico.EmailEmUso as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com esse e-mail"
        ) from erro
    except servico.UsernameEmUso as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Esse nome de usuário já está em uso"
        ) from erro

    try:
        return servico.abrir_sessao(usuario)
    except servico.SessaoIndisponivel as erro:
        # A conta foi criada; só a sessão falhou. O aluno entra pelo login.
        raise SESSAO_INDISPONIVEL from erro


@router.post("/login", response_model=Sessao, dependencies=[_limite("login")])
def entrar(dados: Login, db: Session = Depends(get_db)) -> Sessao:
    try:
        usuario = servico.autenticar(db, email=dados.email, senha=dados.senha)
    except servico.CredenciaisInvalidas as erro:
        raise CREDENCIAIS_INVALIDAS from erro
    except servico.LoginBloqueado as erro:
        minutos = max(erro.segundos // 60, 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas erradas. Tente de novo em {minutos} min "
            "ou redefina a senha.",
            headers={"Retry-After": str(erro.segundos)},
        ) from erro

    cancelou = conta.cancelar_exclusao_se_agendada(db, usuario)
    try:
        sessao = servico.abrir_sessao(usuario, lembrar=dados.lembrar)
    except servico.SessaoIndisponivel as erro:
        raise SESSAO_INDISPONIVEL from erro
    if cancelou:
        sessao.aviso = AVISO_EXCLUSAO_CANCELADA
    return sessao


@router.post("/refresh", response_model=Sessao, dependencies=[_limite("refresh")])
def renovar(dados: Renovacao, db: Session = Depends(get_db)) -> Sessao:
    try:
        return servico.renovar_sessao(db, dados.refresh_token)
    except servico.SessaoExpirada as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada, entre de novo"
        ) from erro
    except servico.SessaoIndisponivel as erro:
        raise SESSAO_INDISPONIVEL from erro


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def sair(dados: Renovacao) -> Response:
    """Encerra a sessão. Responde 204 mesmo com token já inválido: o fim é o mesmo."""
    servico.encerrar_sessao(dados.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/eu", response_model=UsuarioAutenticado)
def eu(usuario: UsuarioAtual) -> UsuarioAutenticado:
    """Rota protegida de referência: é o que o frontend chama ao abrir o app."""
    return UsuarioAutenticado.model_validate(usuario)


@router.post(
    "/esqueci-senha",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[_limite("esqueci-senha")],
)
def esqueci_senha(dados: EsqueciSenha, db: Session = Depends(get_db)) -> dict[str, str]:
    """Começa a recuperação. Sempre 202, tenha o e-mail conta ou não."""
    token = servico.criar_token_de_recuperacao(db, dados.email)

    if token is not None:
        # Enquanto não existe serviço de e-mail, o link vai para o log. Trocar
        # isso pelo envio é a única mudança que essa rota ainda precisa.
        #
        # WARNING e não INFO: o uvicorn só configura os loggers dele, e o INFO
        # de um logger da aplicação não aparece em lugar nenhum.
        logger.warning(
            "Link de recuperação de senha: %s/redefinir-senha?token=%s",
            settings.frontend_origin,
            token,
        )

    return {"detail": "Se houver conta com esse e-mail, o link de recuperação foi enviado"}


@router.post(
    "/redefinir-senha",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_limite("redefinir-senha")],
)
def redefinir_senha(dados: RedefinirSenha, db: Session = Depends(get_db)) -> Response:
    try:
        servico.redefinir_senha(db, token=dados.token, senha=dados.senha)
    except servico.SenhaFraca as erro:
        raise _senha_fraca(erro) from erro
    except servico.TokenDeSenhaInvalido as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de recuperação inválido ou expirado",
        ) from erro

    return Response(status_code=status.HTTP_204_NO_CONTENT)
