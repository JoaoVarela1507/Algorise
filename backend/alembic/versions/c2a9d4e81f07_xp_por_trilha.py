"""xp por trilha

Revision ID: c2a9d4e81f07
Revises: b5cf497366ef
Create Date: 2026-10-09 02:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2a9d4e81f07"
down_revision: str | None = "b5cf497366ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nulo por enquanto: o XP que já existe no banco foi ganho antes de a coluna
    # existir, e não dá para adivinhar a trilha dele sem reprocessar. Os eventos
    # novos chegam preenchidos, e o ranking por trilha só conta esses.
    op.add_column("xp_eventos", sa.Column("trilha_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_xp_eventos_trilha_id_trilhas"),
        "xp_eventos",
        "trilhas",
        ["trilha_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_xp_eventos_trilha_usuario", "xp_eventos", ["trilha_id", "usuario_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_xp_eventos_trilha_usuario", table_name="xp_eventos")
    op.drop_constraint(
        op.f("fk_xp_eventos_trilha_id_trilhas"), "xp_eventos", type_="foreignkey"
    )
    op.drop_column("xp_eventos", "trilha_id")
