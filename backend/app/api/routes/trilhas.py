from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.trilha import Trilha, TrilhaDetalhe
from app.services import trilhas as servico

router = APIRouter(prefix="/trilhas", tags=["trilhas"])


@router.get("", response_model=list[Trilha])
def listar_trilhas(
    db: Session = Depends(get_db),
    busca: str | None = Query(default=None, description="Filtra por nome ou disciplina"),
    periodo: int | None = Query(default=None, ge=1, le=8, description="Período letivo"),
) -> list[Trilha]:
    resultados = servico.listar_trilhas(db, busca=busca, periodo=periodo)
    return [
        Trilha.model_validate(trilha).model_copy(update={"total_modulos": total})
        for trilha, total in resultados
    ]


@router.get("/{slug}", response_model=TrilhaDetalhe)
def obter_trilha(slug: str, db: Session = Depends(get_db)) -> TrilhaDetalhe:
    trilha = servico.obter_trilha(db, slug)
    if trilha is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trilha não encontrada")

    detalhe = TrilhaDetalhe.model_validate(trilha)
    # O primeiro passo nasce liberado; o resto depende do progresso do aluno,
    # que entra junto com a autenticação (#10) e o progresso (#30).
    for indice, modulo in enumerate(detalhe.modulos):
        modulo.bloqueado = indice > 0
    return detalhe.model_copy(update={"total_modulos": len(detalhe.modulos)})
