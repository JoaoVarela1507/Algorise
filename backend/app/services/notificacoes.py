"""Notificações do aluno (#37).

Cada notificação fica gravada, para o centro de notificações mostrar o que
chegou com o aluno offline, e é publicada no canal `notificacoes:{usuario_id}`
com o próprio tipo como nome do evento (`conquista.desbloqueada`,
`certificado.liberado`, `streak.risco`). As abas abertas mostram na hora.

`xp.ganho` também sai nesse canal, mas não vira notificação gravada: é o
contador e a barra de nível se mexendo, sem nada para ler depois.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Notificacao
from app.schemas.pagina import Paginacao
from app.services.tempo_real import publicar

CONQUISTA = "conquista.desbloqueada"
CERTIFICADO = "certificado.liberado"
STREAK_EM_RISCO = "streak.risco"


class NaoEncontrada(Exception):
    """A notificação não existe ou é de outro aluno."""


def canal_de(usuario_id: int) -> str:
    return f"notificacoes:{usuario_id}"


def notificar(
    db: Session,
    usuario_id: int,
    *,
    tipo: str,
    titulo: str,
    mensagem: str,
    dados: dict[str, Any] | None = None,
) -> Notificacao:
    """Grava e publica. Publica depois do commit, para o aviso não chegar antes do dado."""
    notificacao = Notificacao(
        usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensagem=mensagem, dados=dados or {}
    )
    db.add(notificacao)
    db.commit()
    publicar(canal_de(usuario_id), tipo, como_payload(notificacao))
    return notificacao


def como_payload(notificacao: Notificacao) -> dict[str, Any]:
    return {
        "id": notificacao.id,
        "tipo": notificacao.tipo,
        "titulo": notificacao.titulo,
        "mensagem": notificacao.mensagem,
        "dados": notificacao.dados,
        "lida": notificacao.lida_em is not None,
        "criado_em": notificacao.criado_em.isoformat() if notificacao.criado_em else None,
    }


def listar(
    db: Session, usuario_id: int, pagina: Paginacao, *, so_nao_lidas: bool = False
) -> tuple[list[Notificacao], int]:
    """Da mais recente para a mais antiga."""
    consulta = select(Notificacao).where(Notificacao.usuario_id == usuario_id)
    if so_nao_lidas:
        consulta = consulta.where(Notificacao.lida_em.is_(None))
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    itens = db.scalars(
        consulta.order_by(Notificacao.id.desc())
        .offset(pagina.deslocamento)
        .limit(pagina.tamanho_pagina)
    ).all()
    return list(itens), total or 0


def nao_lidas(db: Session, usuario_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Notificacao.id)).where(
                Notificacao.usuario_id == usuario_id, Notificacao.lida_em.is_(None)
            )
        )
        or 0
    )


def marcar_lida(db: Session, usuario_id: int, notificacao_id: int) -> Notificacao:
    notificacao = db.get(Notificacao, notificacao_id)
    if notificacao is None or notificacao.usuario_id != usuario_id:
        raise NaoEncontrada
    if notificacao.lida_em is None:
        notificacao.lida_em = datetime.now(UTC)
        db.commit()
    return notificacao


def marcar_todas(db: Session, usuario_id: int) -> int:
    resultado = db.execute(
        update(Notificacao)
        .where(Notificacao.usuario_id == usuario_id, Notificacao.lida_em.is_(None))
        .values(lida_em=datetime.now(UTC))
    )
    db.commit()
    return resultado.rowcount or 0
