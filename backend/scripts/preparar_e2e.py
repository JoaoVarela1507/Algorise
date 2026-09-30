"""Cria o banco do E2E do zero, a partir dos modelos.

`create_all` em vez de `alembic upgrade`, por um motivo específico: a migração de
RLS é PostgreSQL puro (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) e não roda em
SQLite. Amarrar o E2E ao PostgreSQL só para isso obrigaria todo mundo a subir
container para rodar teste de navegador.

As migrações continuam sendo verificadas onde importa: o CI roda `upgrade`,
`downgrade` e `upgrade` contra um PostgreSQL de verdade.

    python scripts/preparar_e2e.py [caminho-do-banco.db]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine

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


if __name__ == "__main__":
    main()
