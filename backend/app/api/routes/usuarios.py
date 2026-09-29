"""Perfil do aluno logado (tela 18) e o que o onboarding grava (telas 7 a 15)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.schemas.perfil import AtualizacaoPerfil, Perfil
from app.services import perfil as servico

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/eu", response_model=Perfil)
def obter_perfil(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Perfil:
    return servico.montar_perfil(db, usuario)


@router.patch("/eu", response_model=Perfil)
def atualizar_perfil(
    dados: AtualizacaoPerfil, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Perfil:
    try:
        return servico.atualizar_perfil(db, usuario, dados)
    except servico.CursoSemInstituicao as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe a instituição antes do curso",
        ) from erro
