"""Autenticação: e-mail e senha, sessão, login social e "Esqueceu a senha?".

A regra mora em `app/services/auth.py`; aqui é só a tradução para HTTP.
"""

import logging
from typing import Any
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core import oauth
from app.core.config import settings
from app.core.database import get_db
from app.models import ProvedorOAuth
from app.schemas.auth import (
    EsqueciSenhaEntrada,
    LoginEntrada,
    RedefinirSenhaEntrada,
    RefreshEntrada,
    RegistroEntrada,
    Sessao,
)
from app.schemas.usuario import Usuario
from app.services import auth as servico

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSAO_INVALIDA = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão inválida ou expirada. Entre de novo.",
    headers={"WWW-Authenticate": "Bearer"},
)

_SESSAO_INDISPONIVEL = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Não foi possível abrir a sessão agora. Tente de novo em instantes.",
)


# --- e-mail e senha (#88) -----------------------------------------------------


@router.post("/register", response_model=Sessao, status_code=status.HTTP_201_CREATED)
def registrar(dados: RegistroEntrada, db: Session = Depends(get_db)) -> Sessao:
    try:
        usuario = servico.registrar(db, dados)
        return servico.abrir_sessao(usuario, estendido=dados.manter_conectado)
    except servico.ContaJaExiste as erro:
        detalhe = (
            "Este e-mail já está cadastrado."
            if erro.campo == "email"
            else "Este nome de usuário já está em uso."
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detalhe) from erro
    except servico.SessaoIndisponivel as erro:
        # A conta foi criada; só a sessão falhou. O aluno entra pelo login.
        raise _SESSAO_INDISPONIVEL from erro


@router.post("/login", response_model=Sessao)
def login(dados: LoginEntrada, db: Session = Depends(get_db)) -> Sessao:
    try:
        usuario = servico.autenticar(db, dados.email, dados.senha)
        return servico.abrir_sessao(usuario, estendido=dados.manter_conectado)
    except servico.CredenciaisInvalidas as erro:
        # Mesma resposta para senha errada e para e-mail sem conta.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos."
        ) from erro
    except servico.SessaoIndisponivel as erro:
        raise _SESSAO_INDISPONIVEL from erro


# --- sessão (#89) -------------------------------------------------------------


@router.post("/refresh", response_model=Sessao)
def renovar(dados: RefreshEntrada, db: Session = Depends(get_db)) -> Sessao:
    try:
        return servico.renovar(db, dados.refresh_token)
    except servico.SessaoInvalida as erro:
        raise _SESSAO_INVALIDA from erro
    except servico.SessaoIndisponivel as erro:
        raise _SESSAO_INDISPONIVEL from erro


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(dados: RefreshEntrada) -> Response:
    servico.encerrar(dados.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/eu", response_model=Usuario)
def eu(usuario: UsuarioAtual) -> Usuario:
    """Rota protegida de referência: quem é o dono do access token."""
    return Usuario.do_modelo(usuario)


# --- recuperação de senha (#92) -----------------------------------------------


@router.post("/esqueci-senha", status_code=status.HTTP_202_ACCEPTED)
def esqueci_senha(dados: EsqueciSenhaEntrada, tarefas: BackgroundTasks) -> dict[str, str]:
    # Sempre 202 e sempre a mesma mensagem; o trabalho fica para depois da
    # resposta, para nem o tempo dela diferenciar e-mail com e sem conta.
    tarefas.add_task(servico.solicitar_redefinicao, dados.email)
    return {"detail": "Se o e-mail tiver conta, enviaremos um link para redefinir a senha."}


@router.post("/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(dados: RedefinirSenhaEntrada, db: Session = Depends(get_db)) -> Response:
    try:
        servico.redefinir_senha(db, dados.token, dados.nova_senha)
    except servico.LinkInvalido as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link inválido ou expirado. Peça um novo.",
        ) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- login social (#90 e #91) -------------------------------------------------


@router.get("/{provedor}/login", status_code=status.HTTP_302_FOUND)
async def iniciar_oauth(provedor: ProvedorOAuth, request: Request) -> RedirectResponse:
    """Botão da tela 5: manda o aluno para a tela de consentimento do provedor."""
    cliente = oauth.cliente(provedor)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Login com {provedor.value} não está configurado.",
        )

    # Montado a partir de `API_URL`, não do request: atrás de proxy o host do
    # request é o interno, e o provedor recusaria o callback.
    callback = f"{settings.api_url}/auth/{provedor.value}/callback"
    return await cliente.authorize_redirect(request, callback)


@router.get("/{provedor}/callback", include_in_schema=False)
async def callback_oauth(
    provedor: ProvedorOAuth, request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    """Volta do provedor. Termina sempre num redirect para o frontend.

    Os tokens vão no fragmento (`#`), não na query: o fragmento não é enviado ao
    servidor do frontend nem aparece em log de proxy. O frontend lê e limpa a
    URL com `history.replaceState`.
    """
    cliente = oauth.cliente(provedor)
    if cliente is None:
        return _voltar_ao_frontend(erro="provedor_nao_configurado")

    try:
        token = await cliente.authorize_access_token(request)
        perfil = await (_perfil_github if provedor is ProvedorOAuth.github else _perfil_google)(
            cliente, token
        )
    except OAuthError as erro:
        # Inclui o aluno ter clicado em "cancelar" e o `state` não bater.
        logger.warning("OAuth %s recusado: %s", provedor.value, erro)
        return _voltar_ao_frontend(erro="acesso_negado")

    if perfil is None:
        return _voltar_ao_frontend(erro="email_nao_verificado")

    def entrar() -> Sessao:
        usuario = servico.entrar_com_provedor(db, provedor=provedor, **perfil)
        return servico.abrir_sessao(usuario)

    try:
        # O banco é síncrono; fora do threadpool ele travaria o event loop.
        sessao = await run_in_threadpool(entrar)
    except servico.EmailNaoVerificado:
        return _voltar_ao_frontend(erro="email_nao_verificado")
    except servico.ProvedorJaVinculado:
        return _voltar_ao_frontend(erro="provedor_ja_vinculado")
    except servico.SessaoIndisponivel:
        return _voltar_ao_frontend(erro="sessao_indisponivel")

    return _voltar_ao_frontend(
        access_token=sessao.access_token,
        refresh_token=sessao.refresh_token,
        expira_em=str(sessao.expira_em),
    )


async def _perfil_github(cliente: Any, token: dict[str, Any]) -> dict[str, Any] | None:
    perfil = (await cliente.get("user", token=token)).json()

    # O e-mail do perfil vem nulo quando é privado, e mesmo quando vem não diz se
    # foi verificado. `/user/emails` responde as duas coisas.
    emails = (await cliente.get("user/emails", token=token)).json()
    verificados = [e for e in emails if e.get("verified")]
    escolhido = next((e for e in verificados if e.get("primary")), None) or next(
        iter(verificados), None
    )
    if escolhido is None:
        return None

    return {
        "id_externo": str(perfil["id"]),
        "email": escolhido["email"],
        "email_verificado": True,
        "nome": perfil.get("name") or perfil.get("login"),
        "avatar_url": perfil.get("avatar_url"),
        "username_sugerido": perfil.get("login"),
    }


async def _perfil_google(_cliente: Any, token: dict[str, Any]) -> dict[str, Any] | None:
    # O Authlib já validou o id_token (assinatura, `aud`, `nonce`) e o expôs
    # como `userinfo`.
    info = token.get("userinfo") or {}
    if not info.get("email"):
        return None

    return {
        "id_externo": str(info["sub"]),
        "email": info["email"],
        # O serviço recusa quando isso é falso (#91).
        "email_verificado": bool(info.get("email_verified")),
        "nome": info.get("name"),
        "avatar_url": info.get("picture"),
        "username_sugerido": None,
    }


def _voltar_ao_frontend(**parametros: str) -> RedirectResponse:
    destino = f"{settings.frontend_origin}/auth/callback#{urlencode(parametros)}"
    return RedirectResponse(destino, status_code=status.HTTP_302_FOUND)
