"""Rotas de operação, fora do contrato versionado.

Ficam na raiz de propósito: o healthcheck do Docker, o alvo do balanceador e o
carimbo de build não devem mudar de endereço quando a API subir de versão.
"""

from fastapi import APIRouter

from app.api.infra import health, versao

router = APIRouter()

router.include_router(health.router)
router.include_router(versao.router)
