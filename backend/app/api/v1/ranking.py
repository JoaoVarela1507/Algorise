"""Ranking de XP (telas 16 e 17), geral ou de uma trilha."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioOpcional
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.ranking import Ranking
from app.services import ranking as servico
from app.services import trilhas as servico_trilhas

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get(
    "",
    response_model=Ranking,
    summary="Pódio e lista rolável",
    description=(
        "Sem `trilha`, soma todo o XP do aluno. Com `trilha`, só o ganho nela. "
        "Com token, a posição do próprio aluno vem junto, mesmo fora da página."
    ),
)
def obter_ranking(
    usuario: UsuarioOpcional,
    db: Session = Depends(get_db),
    limite: int = Query(default=20, ge=1, le=100, description="Tamanho da página"),
    deslocamento: int = Query(default=0, ge=0, description="Quantos pular na lista rolável"),
    trilha: str | None = Query(
        default=None, description="Slug da trilha, para o ranking dela (telas 16 e 17)"
    ),
) -> Ranking:
    trilha_id = None
    if trilha is not None:
        encontrada = servico_trilhas.obter_trilha(db, trilha)
        if encontrada is None or not encontrada.publicada:
            raise ErroDeNegocio(
                status_code=status.HTTP_404_NOT_FOUND,
                code="trilha_nao_encontrada",
                message="Trilha não encontrada",
                details={"slug": trilha},
            )
        trilha_id = encontrada.id

    return servico.obter_ranking(
        db,
        trilha_id=trilha_id,
        limite=limite,
        deslocamento=deslocamento,
        # Quem está logado vê a própria posição sem precisar pedir: era o
        # `usuario_id` na query, que dava para qualquer um espiar a de outro.
        usuario_id=usuario.id if usuario else None,
    )
