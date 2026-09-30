"""Apaga de vez as contas cujo prazo de exclusão passou (#40).

    python -m app.tarefas.expurgo

Roda uma vez e sai; o agendamento (cron diário, scheduler da hospedagem) é de
quem faz o deploy. É idempotente: rodar duas vezes seguidas não apaga nada a
mais, e atrasar um dia só adia o expurgo.
"""

import logging

from app.core.database import SessionLocal
from app.services.conta import expurgar_vencidas

logger = logging.getLogger("app.tarefas.expurgo")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with SessionLocal() as db:
        apagadas = expurgar_vencidas(db)
    logger.info("Contas expurgadas: %s", apagadas)


if __name__ == "__main__":
    main()
