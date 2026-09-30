from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import infra, v1
from app.core.config import settings
from app.core.protecao_http import ProtecaoHTTP

app = FastAPI(title=settings.app_name, version=settings.app_version)

# O Authlib guarda o `state` do OAuth2 num cookie de sessão assinado. Ele só
# existe entre o início do fluxo e o callback; nada da aplicação depende dele.
#
# `same_site="lax"` é o mínimo para o cookie sobreviver ao redirecionamento de
# volta do provedor, e `https_only` fica ligado fora de desenvolvimento.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret,
    session_cookie="algorise_oauth",
    same_site="lax",
    https_only=settings.environment == "production",
    max_age=600,
)

# Só a origem do frontend, e só o que ele usa (#40). O `*` em produção é
# recusado já na configuração (ver `Settings._conferir_segredo`).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    # O navegador guarda o preflight por 10 minutos em vez de repetir o
    # OPTIONS a cada chamada autenticada.
    max_age=600,
)

# Por último = mais externo: os headers de segurança valem também para as
# respostas de erro do CORS, e o teto de tamanho barra o corpo antes de tudo.
app.add_middleware(ProtecaoHTTP)

app.include_router(infra.router)
app.include_router(v1.router)
