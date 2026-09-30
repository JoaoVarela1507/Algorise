from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ranking import Ranking
from app.services import ranking as servico

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("", response_model=Ranking)
def obter_ranking(
    db: Session = Depends(get_db),
    limite: int = Query(default=20, ge=1, le=100, description="Tamanho da página"),
    deslocamento: int = Query(default=0, ge=0, description="Quantos pular na lista rolável"),
    # Temporário: sai quando a autenticação (#10) puder dizer quem é o aluno.
    usuario_id: int | None = Query(default=None, description="Aluno cuja posição também entra"),
) -> Ranking:
    return servico.obter_ranking(
        db, limite=limite, deslocamento=deslocamento, usuario_id=usuario_id
    )
