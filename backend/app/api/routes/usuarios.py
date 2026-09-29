"""Direitos do titular sobre a própria conta (LGPD, #40).

O resto do perfil (`GET/PATCH /usuarios/me`, preferências) vem com a #27.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.schemas.auth import ExclusaoConta
from app.services import conta

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class ExclusaoAgendada(BaseModel):
    detail: str
    exclusao_agendada_para: datetime


@router.get("/me/dados")
def exportar_meus_dados(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> JSONResponse:
    """Tudo o que o Algorise guarda sobre o aluno, para baixar como arquivo."""
    return JSONResponse(
        conta.exportar_dados(db, usuario),
        headers={
            "Content-Disposition": 'attachment; filename="algorise-meus-dados.json"',
            # Dado pessoal: nem o navegador nem proxy no caminho guardam cópia.
            "Cache-Control": "no-store",
        },
    )


@router.delete("/me", response_model=ExclusaoAgendada, status_code=status.HTTP_202_ACCEPTED)
def excluir_minha_conta(
    dados: ExclusaoConta, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> ExclusaoAgendada:
    """Pede a exclusão da conta: desativa agora e apaga tudo no fim do prazo.

    202 e não 204: o pedido foi aceito, mas a exclusão só se completa no expurgo.
    """
    try:
        data = conta.agendar_exclusao(db, usuario, confirmacao=dados.confirmacao, senha=dados.senha)
    except conta.ConfirmacaoInvalida as erro:
        detalhe = (
            "Senha incorreta."
            if str(erro) == "senha"
            else f'Digite "{conta.CONFIRMACAO_DE_EXCLUSAO}" para confirmar.'
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalhe) from erro

    return ExclusaoAgendada(
        detail="Conta desativada. Os dados serão apagados na data indicada; "
        "entrar de novo antes disso cancela a exclusão.",
        exclusao_agendada_para=data,
    )
