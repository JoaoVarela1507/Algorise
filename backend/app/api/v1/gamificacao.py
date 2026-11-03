"""XP, nível e streak do aluno (telas 16 e 20)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.schemas.gamificacao import Conquista, MetaDiaria, Painel
from app.services import conquistas as servico_conquistas
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


@router.get(
    "/meta-diaria",
    response_model=MetaDiaria,
    summary="XP, desafios e minutos de hoje",
    description="O dia vira à meia-noite no fuso do aluno, como o streak.",
)
def obter_meta_diaria(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> MetaDiaria:
    return MetaDiaria(**vars(servico.meta_diaria(db, usuario)))


@router.get(
    "/conquistas",
    response_model=list[Conquista],
    summary="Conquistas do aluno, desbloqueadas ou não",
)
def listar_conquistas(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> list[Conquista]:
    return [Conquista(**vars(c)) for c in servico_conquistas.conquistas(db, usuario)]
