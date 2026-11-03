"""Resumo do que saiu da janela de contexto do chat (#33).

Roda depois da resposta ser gravada, sem o aluno esperar: no SSE como tarefa
depois da resposta, no WebSocket depois do evento final. Se o modelo falhar, a
conversa segue com o resumo antigo, e a próxima resposta tenta de novo.
"""

import logging

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.ia import IAIndisponivel, ProvedorIA
from app.ia.skills import resumir_conversa
from app.models import Conversa, MensagemChat, PapelMensagem

logger = logging.getLogger(__name__)


async def atualizar(fabrica: sessionmaker[Session], provedor: ProvedorIA, conversa_id: int) -> bool:
    """Resume as mensagens que saíram da janela desde o último resumo. `True` se resumiu."""
    pendente = await run_in_threadpool(_pendente, fabrica, conversa_id)
    if pendente is None:
        return False
    resumo_anterior, falas, ate_id = pendente
    try:
        partes = [
            pedaco
            async for pedaco in provedor.gerar(
                resumir_conversa.mensagens(resumo_anterior, falas),
                max_tokens=resumir_conversa.MAXIMO_DE_TOKENS,
            )
        ]
    except IAIndisponivel as erro:
        logger.warning("Resumo da conversa %s ficou para depois: %s", conversa_id, erro)
        return False
    resumo = "".join(partes).strip()
    if not resumo:
        return False
    await run_in_threadpool(_gravar, fabrica, conversa_id, resumo, ate_id)
    return True


def _pendente(
    fabrica: sessionmaker[Session], conversa_id: int
) -> tuple[str | None, list[tuple[str, str]], int] | None:
    with fabrica() as db:
        conversa = db.get(Conversa, conversa_id)
        if conversa is None:
            return None
        janela = db.scalars(
            select(MensagemChat.id)
            .where(MensagemChat.conversa_id == conversa_id)
            .order_by(MensagemChat.id.desc())
            .limit(settings.chat_janela_historico)
        ).all()
        if len(janela) < settings.chat_janela_historico:
            return None
        fora = db.scalars(
            select(MensagemChat)
            .where(
                MensagemChat.conversa_id == conversa_id,
                MensagemChat.id < min(janela),
                MensagemChat.id > (conversa.resumo_ate_id or 0),
            )
            .order_by(MensagemChat.id)
        ).all()
        if not fora:
            return None
        falas = [
            ("aluno" if m.papel is PapelMensagem.usuario else "tutor", m.conteudo) for m in fora
        ]
        return conversa.resumo, falas, fora[-1].id


def _gravar(fabrica: sessionmaker[Session], conversa_id: int, resumo: str, ate_id: int) -> None:
    with fabrica() as db:
        conversa = db.get(Conversa, conversa_id)
        if conversa is None:
            return
        conversa.resumo = resumo
        conversa.resumo_ate_id = ate_id
        db.commit()
