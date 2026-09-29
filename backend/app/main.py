from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, health, ranking, trilhas, versao
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Só o login social usa: guarda o `state` do OAuth entre o redirect para o
# provedor e o callback. A sessão do aluno em si é o par de JWT, não este cookie.
# `lax` é o que deixa o cookie voltar no redirect vindo do GitHub/Google.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret,
    session_cookie="algorise_oauth",
    max_age=60 * 10,
    same_site="lax",
    https_only=settings.environment == "production",
)

app.include_router(health.router)
app.include_router(versao.router)
app.include_router(auth.router)
app.include_router(trilhas.router)
app.include_router(ranking.router)
