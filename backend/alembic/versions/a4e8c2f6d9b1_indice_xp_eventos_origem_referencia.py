"""índice de xp_eventos por origem e referência

O ranking por trilha (`ranking.por_trilha`) soma o XP de uma trilha filtrando
`xp_eventos` por `origem` e `referencia_id`, sem `usuario_id` na frente — o
índice que já existia (`usuario_id, criado_em`) não ajuda, e a consulta lia a
tabela inteira.

Revision ID: a4e8c2f6d9b1
Revises: e7a3c0d6f2b5
Create Date: 2026-11-17 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a4e8c2f6d9b1"
down_revision: str | None = "e7a3c0d6f2b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_xp_eventos_origem_referencia", "xp_eventos", ["origem", "referencia_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_xp_eventos_origem_referencia", table_name="xp_eventos")
