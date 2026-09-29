"""Rotas do login social (botões GitHub e Google da tela 5).

O desenho do fluxo:

1. o frontend manda o aluno para `/auth/{provedor}/login`;
2. a API redireciona para o provedor, guardando o `state` na sessão assinada;
3. o provedor volta em `/auth/{provedor}/callback`;
4. a API resolve a conta e devolve o aluno ao frontend com o par de tokens no
   fragmento da URL (`#access_token=...`).

O fragmento não é enviado ao servidor nem entra em log de proxy, diferente da
query string — é por isso que os tokens vão nele.
"""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services import auth as servico_auth
from app.services import oauth as servico

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/{provedor}/login")
async def iniciar(provedor: str, request: Request) -> RedirectResponse:
    """Manda o aluno para o provedor."""
    cliente = _cliente(provedor)
    retorno = request.url_for("callback_oauth", provedor=provedor)
    return await cliente.authorize_redirect(request, str(retorno))


@router.get("/{provedor}/callback", name="callback_oauth")
async def callback(
    provedor: str, request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    """Recebe o provedor de volta, resolve a conta e devolve o aluno ao frontend."""
    cliente = _cliente(provedor)

    try:
        token = await cliente.authorize_access_token(request)
    except Exception as erro:
        # `state` inválido, código expirado, aluno que cancelou na tela do
        # provedor: nada disso é erro nosso, e nenhum detalhe deve vazar.
        logger.info("Falha no callback do %s: %s", provedor, erro)
        return _voltar_com_erro("falha_no_login")

    try:
        perfil = (
            await servico.perfil_do_github(token)
            if provedor == servico.GITHUB
            else servico.perfil_do_google(token)
        )
    except servico.PerfilIncompleto:
        return _voltar_com_erro("email_nao_verificado")

    usuario = servico.vincular_ou_criar(db, perfil)

    try:
        sessao = servico_auth.abrir_sessao(usuario, lembrar=True)
    except servico_auth.SessaoExpirada:
        return _voltar_com_erro("sessao_indisponivel")

    return _voltar_para_o_frontend(
        access_token=sessao.access_token,
        refresh_token=sessao.refresh_token,
        expira_em=str(sessao.expira_em),
    )


def _cliente(provedor: str):
    try:
        return servico.cliente(provedor)
    except servico.ProvedorIndisponivel as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Login com {provedor} não está configurado neste ambiente",
        ) from erro


def _voltar_para_o_frontend(**parametros: str) -> RedirectResponse:
    destino = f"{settings.frontend_origin}{settings.oauth_retorno_frontend}"
    # 303 força o navegador a seguir com GET, seja qual for o método de origem.
    return RedirectResponse(
        f"{destino}#{urlencode(parametros)}", status_code=status.HTTP_303_SEE_OTHER
    )


def _voltar_com_erro(codigo: str) -> RedirectResponse:
    """Erro vai na query, não no fragmento: o frontend só precisa exibir a mensagem."""
    destino = f"{settings.frontend_origin}{settings.oauth_retorno_frontend}"
    return RedirectResponse(
        f"{destino}?{urlencode({'erro': codigo})}", status_code=status.HTTP_303_SEE_OTHER
    )
