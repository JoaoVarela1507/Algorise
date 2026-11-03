"""partes pendentes da ementa

Revision ID: e7a3c0d6f2b5
Revises: d6f2b9c5e1a4
Create Date: 2026-11-03 21:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e7a3c0d6f2b5"
down_revision: str | None = "d6f2b9c5e1a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ementas",
        sa.Column("partes_pendentes", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("ementas", "partes_pendentes")
