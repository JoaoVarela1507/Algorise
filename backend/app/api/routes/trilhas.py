from fastapi import APIRouter

from app.schemas.trilha import Trilha

router = APIRouter(prefix="/trilhas", tags=["trilhas"])


@router.get("", response_model=list[Trilha])
def listar_trilhas() -> list[Trilha]:
    # TODO: substituir por consulta real assim que houver persistência de dados.
    return []
