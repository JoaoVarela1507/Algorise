from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import infra, v1
from app.core.config import settings
from app.core.erros import registrar_handlers
from app.core.openapi import RESPOSTAS_PADRAO, TAGS, gerar_operation_id
from app.core.protecao_http import ProtecaoHTTP
from app.core.rastreio import Rastreio

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API do Algorise. As rotas de negócio vivem sob `/api/v1`; `/health`, "
        "`/ready` e `/version` ficam fora do prefixo por serem de operação."
    ),
    openapi_tags=TAGS,
    # Nome da função vira `operation_id`, que vira nome de função no cliente
    # TypeScript gerado (ver `app/core/openapi.py`).
    generate_unique_id_function=gerar_operation_id,
    responses=RESPOSTAS_PADRAO,
)

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

# Mais externo que todos: o id precisa existir antes de qualquer coisa poder
# falhar, e o tempo medido é o da requisição inteira, middlewares inclusos.
app.add_middleware(Rastreio)

# Todo erro sai no formato único (ver `app/core/erros.py`).
registrar_handlers(app)

app.include_router(infra.router)
app.include_router(v1.router)
