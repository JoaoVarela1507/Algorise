from fastapi import APIRouter

from app.core.config import settings
from app.schemas.versao import Versao

router = APIRouter(tags=["version"])


@router.get("/version", response_model=Versao)
def versao() -> Versao:
    return Versao(
        nome=settings.app_name,
        versao=settings.app_version,
        commit=settings.git_commit,
        build=settings.build_time,
        ambiente=settings.environment,
    )
