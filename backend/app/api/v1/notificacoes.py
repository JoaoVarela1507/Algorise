"""Centro de notificações (#37): o que chegou, inclusive offline, e a marcação de lida.

Ao vivo, as mesmas notificações chegam pelo WebSocket, no canal
`notificacoes:{usuario_id}`.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.notificacoes import ContagemDeNotificacoes, Marcadas, NotificacaoSaida
from app.schemas.pagina import Pagina, PaginacaoAtual
from app.services import notificacoes as servico

router = APIRouter(prefix="/notificacoes", tags=["notificacoes"])


@router.get(
    "",
    response_model=Pagina[NotificacaoSaida],
    summary="Notificações do aluno, da mais recente",
)
def listar_notificacoes(
    paginacao: PaginacaoAtual,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
    nao_lidas: bool = Query(default=False, description="Só as que ainda não foram lidas"),
) -> Pagina[NotificacaoSaida]:
    itens, total = servico.listar(db, usuario.id, paginacao, so_nao_lidas=nao_lidas)
    return Pagina[NotificacaoSaida].montar(
        [NotificacaoSaida.model_validate(n) for n in itens],
        pagina=paginacao.pagina,
        tamanho_pagina=paginacao.tamanho_pagina,
        total=total,
    )


@router.get(
    "/contagem",
    response_model=ContagemDeNotificacoes,
    summary="Quantas notificações faltam ler (o número no sino)",
)
def contar_notificacoes(
    usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> ContagemDeNotificacoes:
    return ContagemDeNotificacoes(nao_lidas=servico.nao_lidas(db, usuario.id))


@router.post(
    "/{notificacao_id}/lida",
    response_model=NotificacaoSaida,
    summary="Marca uma notificação como lida",
)
def marcar_notificacao_lida(
    notificacao_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> NotificacaoSaida:
    try:
        return NotificacaoSaida.model_validate(servico.marcar_lida(db, usuario.id, notificacao_id))
    except servico.NaoEncontrada as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="notificacao_nao_encontrada",
            message="Notificação não encontrada",
            details={"id": notificacao_id},
        ) from erro


@router.post("/lidas", response_model=Marcadas, summary="Marca todas como lidas")
def marcar_todas_lidas(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Marcadas:
    return Marcadas(marcadas=servico.marcar_todas(db, usuario.id))
