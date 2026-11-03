"""Ranking de XP: geral, por trilha e a posição do aluno (telas 16 e 17, #31)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual, UsuarioOpcional
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.models import Trilha
from app.schemas.ranking import EntradaRanking, Ranking
from app.services import ranking as servico

router = APIRouter(prefix="/ranking", tags=["ranking"])

Limite = Query(default=20, ge=1, le=100, description="Tamanho da página")
Deslocamento = Query(default=0, ge=0, description="Quantos pular na lista rolável")


@router.get("", response_model=Ranking, summary="Ranking geral (mesmo que `/ranking/geral`)")
def obter_ranking(
    usuario: UsuarioOpcional,
    db: Session = Depends(get_db),
    limite: int = Limite,
    deslocamento: int = Deslocamento,
    usuario_id: int | None = Query(
        default=None, description="Aluno cuja posição também entra; logado, é ele mesmo"
    ),
) -> Ranking:
    alvo = usuario_id if usuario_id is not None else (usuario.id if usuario else None)
    return servico.obter_ranking(db, limite=limite, deslocamento=deslocamento, usuario_id=alvo)


@router.get("/geral", response_model=Ranking, summary="Ranking geral")
def obter_ranking_geral(
    usuario: UsuarioOpcional,
    db: Session = Depends(get_db),
    limite: int = Limite,
    deslocamento: int = Deslocamento,
) -> Ranking:
    return servico.obter_ranking(
        db, limite=limite, deslocamento=deslocamento, usuario_id=usuario.id if usuario else None
    )


@router.get("/me", response_model=EntradaRanking, summary="Posição do aluno no ranking geral")
def obter_minha_posicao(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> EntradaRanking:
    posicao = servico.posicao_geral(db, usuario.id)
    if posicao is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="fora_do_ranking",
            message="Você ainda não está no ranking",
        )
    return posicao


@router.get(
    "/trilhas/{trilha_id}",
    response_model=Ranking,
    summary="Ranking de uma trilha",
    description="Pelo XP ganho nas atividades, nos passos e na conclusão daquela trilha.",
)
def obter_ranking_da_trilha(
    trilha_id: int,
    usuario: UsuarioOpcional,
    db: Session = Depends(get_db),
    limite: int = Limite,
    deslocamento: int = Deslocamento,
) -> Ranking:
    trilha = db.get(Trilha, trilha_id)
    if trilha is None or not trilha.publicada:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="trilha_nao_encontrada",
            message="Trilha não encontrada",
            details={"trilha_id": trilha_id},
        )
    return servico.por_trilha(
        db,
        trilha,
        limite=limite,
        deslocamento=deslocamento,
        usuario_id=usuario.id if usuario else None,
    )
