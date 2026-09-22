from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, health, oauth, ranking, trilhas, versao
from app.core.config import settings

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(versao.router)
app.include_router(trilhas.router)
app.include_router(ranking.router)
app.include_router(auth.router)
app.include_router(oauth.router)
