from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Processo vivo. Não toca no banco: é o healthcheck do container."""
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(resposta: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    """Pronta para servir: o banco respondeu.

    Devolve 503 em vez de estourar exceção, para o orquestrador tirar a
    instância do balanceador sem a API cair.
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        resposta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "indisponivel", "banco": "erro"}

    return {"status": "ok", "banco": "ok"}
