"""xp alcançado em

Revision ID: f2b8d5e1a7c4
Revises: e1a7c4d9f6b3
Create Date: 2026-11-04 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2b8d5e1a7c4"
down_revision: str | None = "e1a7c4d9f6b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios", sa.Column("xp_alcancado_em", sa.DateTime(timezone=True), nullable=True)
    )
    # Quem já tem XP chegou ao saldo atual no último evento: é o desempate do
    # ranking (#31) para as contas que já existem.
    op.execute(
        """
        UPDATE usuarios SET xp_alcancado_em = ultimo.quando
        FROM (
            SELECT usuario_id, MAX(criado_em) AS quando FROM xp_eventos GROUP BY usuario_id
        ) AS ultimo
        WHERE usuarios.id = ultimo.usuario_id
        """
    )


def downgrade() -> None:
    op.drop_column("usuarios", "xp_alcancado_em")
