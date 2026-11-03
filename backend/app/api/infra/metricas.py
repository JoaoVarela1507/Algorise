"""`GET /metrics`, no formato de texto do Prometheus (#39). Ver `app/core/metricas.py`."""

import secrets

from fastapi import APIRouter, Header, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core import metricas
from app.core.config import settings
from app.core.erros import ErroDeNegocio

router = APIRouter(tags=["health"])


@router.get(
    "/metrics",
    summary="Métricas do Prometheus",
    description="Com `METRICAS_TOKEN` definido, pede `Authorization: Bearer <token>`.",
    response_class=Response,
)
def coletar_metricas(authorization: str = Header(default="")) -> Response:
    if settings.metricas_token:
        esperado = f"Bearer {settings.metricas_token}"
        # Comparação em tempo constante: o token não vaza pela demora da resposta.
        if not secrets.compare_digest(authorization.encode(), esperado.encode()):
            raise ErroDeNegocio(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="nao_autorizado",
                message="Token das métricas ausente ou errado",
            )
    return Response(generate_latest(metricas.registro), media_type=CONTENT_TYPE_LATEST)
