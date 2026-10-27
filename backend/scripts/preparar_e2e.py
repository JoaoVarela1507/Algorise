"""Prepara o E2E: banco do zero e Redis de teste limpo.

`create_all` em vez de `alembic upgrade`, por um motivo específico: a migração de
RLS é PostgreSQL puro (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) e não roda em
SQLite. Amarrar o E2E ao PostgreSQL só para isso obrigaria todo mundo a subir
container para rodar teste de navegador.

As migrações continuam sendo verificadas onde importa: o CI roda `upgrade`,
`downgrade` e `upgrade` contra um PostgreSQL de verdade.

O Redis também precisa começar limpo, e não é preciosismo: o banco é recriado a
cada execução, então os ids dos alunos voltam a 1 — e um marcador de streak da
execução anterior faria o check-in de hoje ser ignorado para o "mesmo" aluno.

    python scripts/preparar_e2e.py [caminho-do-banco.db]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine

from app.core.config import settings
from app.models import Base

PADRAO = Path("e2e.db")


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else PADRAO
    # Banco de teste: começa vazio a cada execução, senão o cadastro do E2E
    # esbarra no e-mail da execução anterior.
    destino.unlink(missing_ok=True)

    engine = create_engine(f"sqlite:///{destino}")
    Base.metadata.create_all(engine)
    engine.dispose()

    print(f"Banco do E2E criado em {destino}")
    _limpar_redis()


def _limpar_redis() -> None:
    """Esvazia o banco de teste do Redis — nunca o 0, que é o de verdade.

    A URL do E2E aponta para o índice 1 (ver `playwright.config.ts`). Se alguém
    rodar com o índice 0, este script não apaga nada: melhor um teste frágil do
    que varrer o Redis de desenvolvimento de alguém.
    """
    indice = settings.redis_url.rsplit("/", 1)[-1]
    if indice in ("", "0"):
        print("Redis no índice 0: não vou limpar. O E2E pode herdar estado antigo.")
        return

    import redis

    try:
        redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2).flushdb()
    except Exception as erro:
        print(f"Não deu para limpar o Redis ({erro}); seguindo assim mesmo.")
        return

    print(f"Redis de teste (índice {indice}) limpo")


if __name__ == "__main__":
    main()
