"""XP, nível e streak do aluno (telas 16 e 20)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.schemas.gamificacao import Painel
from app.services import gamificacao as servico

router = APIRouter(prefix="/gamificacao", tags=["gamificacao"])


@router.get(
    "/me",
    response_model=Painel,
    summary="XP, nível e streak do aluno",
    description="Só leitura: não registra acesso nem mexe no streak.",
)
def obter_painel(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Painel:
    return Painel(**vars(servico.painel(db, usuario)))


@router.post(
    "/checkin",
    response_model=Painel,
    status_code=status.HTTP_200_OK,
    summary="Registra o acesso do dia e devolve o streak atualizado",
    description="Chamar várias vezes no mesmo dia conta uma vez só.",
)
def registrar_checkin(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Painel:
    return Painel(**vars(servico.checkin(db, usuario)))
