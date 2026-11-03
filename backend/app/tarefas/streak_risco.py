"""Avisa quem vai perder o streak se não entrar hoje (#37).

    python -m app.tarefas.streak_risco

Roda uma vez e sai; o agendamento é de quem faz o deploy, no fim da tarde no
fuso de `FUSO_HORARIO` (às 20h, por exemplo), para dar tempo de o aluno entrar.
Em risco está quem tem sequência e entrou ontem, mas ainda não hoje. É
idempotente: rodar de novo no mesmo dia não avisa duas vezes.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Notificacao, Streak
from app.services import notificacoes
from app.services.streak import hoje_no_fuso

logger = logging.getLogger("app.tarefas.streak_risco")


def avisar(db: Session, *, hoje: date | None = None) -> int:
    """Notifica os alunos com o streak em risco. Devolve quantos foram avisados."""
    hoje = hoje or hoje_no_fuso()
    em_risco = db.scalars(
        select(Streak).where(
            Streak.dias_consecutivos > 0, Streak.ultimo_acesso == hoje - timedelta(days=1)
        )
    ).all()
    ja_avisados = {
        n.usuario_id
        for n in db.scalars(
            select(Notificacao).where(
                Notificacao.tipo == notificacoes.STREAK_EM_RISCO,
                Notificacao.usuario_id.in_([s.usuario_id for s in em_risco]),
            )
        )
        if n.dados.get("dia") == hoje.isoformat()
    }
    avisados = 0
    for atual in em_risco:
        if atual.usuario_id in ja_avisados:
            continue
        dias = atual.dias_consecutivos
        notificacoes.notificar(
            db,
            atual.usuario_id,
            tipo=notificacoes.STREAK_EM_RISCO,
            titulo="Seu streak está em risco",
            mensagem=f"Entre hoje para não perder a sequência de {dias} dias.",
            dados={"dia": hoje.isoformat(), "dias": dias},
        )
        avisados += 1
    return avisados


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with SessionLocal() as db:
        avisados = avisar(db)
    logger.info("Alunos avisados do streak em risco: %s", avisados)


if __name__ == "__main__":
    main()
