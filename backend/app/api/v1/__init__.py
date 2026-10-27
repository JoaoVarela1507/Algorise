"""Versão 1 da API.

Tudo que é contrato com o frontend vive sob `/api/v1`: mudar o formato de uma
resposta obriga a subir para `/api/v2`, e as duas podem conviver enquanto o
frontend migra.

O que **não** entra aqui é `app/api/infra/`: `/health`, `/ready` e `/version` são
de operação, não de contrato. O healthcheck do container e o alvo do balanceador
não podem mudar de endereço porque a API virou v2.
"""

from fastapi import APIRouter

from app.api.v1 import (
    academico,
    atividades,
    auth,
    chat,
    ementas,
    gamificacao,
    oauth,
    onboarding,
    ranking,
    trilhas,
    usuarios,
)

PREFIXO = "/api/v1"

router = APIRouter(prefix=PREFIXO)

router.include_router(auth.router)
router.include_router(oauth.router)
router.include_router(trilhas.router)
router.include_router(atividades.router)
router.include_router(ranking.router)
router.include_router(gamificacao.router)
router.include_router(usuarios.router)
router.include_router(onboarding.router)
router.include_router(academico.router)
router.include_router(ementas.router)
router.include_router(chat.router)
