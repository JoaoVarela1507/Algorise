"""Fim do onboarding acadêmico (telas 7 a 15), numa chamada só."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.perfil import Onboarding, Perfil
from app.services import perfil as servico_perfil

router = APIRouter(tags=["usuarios"])


@router.post(
    "/onboarding",
    response_model=Perfil,
    summary="Grava nível, modo de trilha, instituição, curso e período",
    description=(
        "Instituição e curso pelo `id` do catálogo ou pelo nome digitado. Pode ser "
        "refeito; `onboarding_concluido_em` guarda a primeira conclusão."
    ),
)
def concluir_onboarding(
    dados: Onboarding, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Perfil:
    try:
        return servico_perfil.concluir_onboarding(db, usuario, dados)
    except servico_perfil.OnboardingInvalido as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=erro.codigo,
            message=str(erro),
        ) from erro
