"""vídeo assistido no progresso do passo

O passo guarda quando o aluno assistiu o vídeo até o fim (#21), para a tela do
passo marcar "assistido" também depois de recarregar. Coluna nova e opcional:
quem roda uma versão anterior do código simplesmente não a lê.

Revision ID: b8f1d3e7a2c4
Revises: a4e8c2f6d9b1
Create Date: 2026-11-17 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8f1d3e7a2c4"
down_revision: str | None = "a4e8c2f6d9b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "progresso_usuario",
        sa.Column("video_assistido_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("progresso_usuario", "video_assistido_em")
