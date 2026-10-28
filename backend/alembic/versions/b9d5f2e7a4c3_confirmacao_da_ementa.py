"""confirmação da ementa

Revision ID: b9d5f2e7a4c3
Revises: a8c4e1d6f3b2
Create Date: 2026-10-28 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b9d5f2e7a4c3"
down_revision: str | None = "a8c4e1d6f3b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A ementa confirmada por último é a base da trilha guiada do aluno (#38).
    op.add_column("ementas", sa.Column("confirmada_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("ementas", "confirmada_em")
