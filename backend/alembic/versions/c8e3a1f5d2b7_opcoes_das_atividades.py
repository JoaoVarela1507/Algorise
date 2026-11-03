"""opções e código das atividades

Revision ID: c8e3a1f5d2b7
Revises: b4d0f7a3c9e2
Create Date: 2026-11-03 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8e3a1f5d2b7"
down_revision: str | None = "b4d0f7a3c9e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # As alternativas da múltipla escolha, os itens da ordenação e o trecho com
    # lacunas: o que faltava para esses tipos terem correção (telas 28 a 33).
    op.add_column("atividades", sa.Column("opcoes", sa.JSON(), nullable=True))
    op.add_column("atividades", sa.Column("codigo", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("atividades", "codigo")
    op.drop_column("atividades", "opcoes")
