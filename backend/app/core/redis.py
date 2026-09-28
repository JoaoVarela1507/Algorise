"""Conexão com o Redis: cliente compartilhado e degradação graciosa.

Aqui o Redis é cache e dado volátil, nunca fonte da verdade — com uma exceção
declarada em `app/services/sessoes.py`. Por isso todo acesso passa por
`executar()`: se o Redis estiver fora, a chamada devolve o padrão combinado e
quem chamou segue pelo caminho lento (o PostgreSQL), em vez de estourar 500.

O cliente é preguiçoso: `from_url` não abre conexão, só o primeiro comando abre.
Isso é o que permite a API subir com o Redis ainda de pé ou nem existindo.
"""

import logging
from collections.abc import Callable

from redis import ConnectionPool, Redis, RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# `decode_responses` devolve str em vez de bytes: todo valor que guardamos é
# texto (JSON, número, id), então converter na borda evita `.decode()` espalhado.
#
# Os timeouts são curtos de propósito (ver `redis_timeout` no config): esperar
# pelo cache custa mais do que consultar o banco.
pool = ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=settings.redis_timeout,
    socket_timeout=settings.redis_timeout,
    # Reaproveitar conexão morta é o caso comum quando o container do Redis
    # reinicia; sem isso o primeiro comando depois do restart falha à toa.
    health_check_interval=30,
    retry_on_timeout=True,
)

cliente = Redis(connection_pool=pool)


def executar[T](operacao: Callable[[Redis], T], *, padrao: T | None = None) -> T | None:
    """Roda `operacao` no Redis; devolve `padrao` se o Redis não responder.

    `OSError` entra junto com `RedisError` porque falha de DNS e de socket na
    primeira conexão chega como erro do sistema, não da biblioteca.
    """
    try:
        return operacao(cliente)
    except (RedisError, OSError) as erro:
        logger.warning("Redis indisponível, seguindo sem cache: %s", erro)
        return padrao


def disponivel() -> bool:
    """Responde ao PING. Usado pelo /ready, que só reporta e não derruba."""
    return executar(lambda r: r.ping(), padrao=False) is True
