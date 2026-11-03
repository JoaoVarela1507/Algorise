"""categorização das partes

Revision ID: a6c3e9d5b2f8
Revises: f5b2d8c4a1e7
Create Date: 2026-11-02 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a6c3e9d5b2f8"
down_revision: str | None = "f5b2d8c4a1e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("partes_video", sa.Column("disciplina", sa.String(length=200), nullable=True))
    op.add_column("partes_video", sa.Column("confianca", sa.Float(), nullable=True))
    op.add_column("partes_video", sa.Column("justificativa", sa.Text(), nullable=True))
    op.add_column("partes_video", sa.Column("aprovada", sa.Boolean(), nullable=True))

    op.add_column(
        "video_lacunas",
        sa.Column("recusada", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    op.create_table(
        "parte_lacunas",
        sa.Column("parte_id", sa.Integer(), nullable=False),
        sa.Column("lacuna_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parte_id"],
            ["partes_video.id"],
            name=op.f("fk_parte_lacunas_parte_id_partes_video"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lacuna_id"],
            ["lacunas.id"],
            name=op.f("fk_parte_lacunas_lacuna_id_lacunas"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("parte_id", "lacuna_id", name=op.f("pk_parte_lacunas")),
    )
    op.create_index(
        op.f("ix_parte_lacunas_lacuna_id"), "parte_lacunas", ["lacuna_id"], unique=False
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE parte_lacunas ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_parte_lacunas_lacuna_id"), table_name="parte_lacunas")
    op.drop_table("parte_lacunas")
    op.drop_column("video_lacunas", "recusada")
    for coluna in ("aprovada", "justificativa", "confianca", "disciplina"):
        op.drop_column("partes_video", coluna)
