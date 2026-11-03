"""partes dos vídeos

Revision ID: f5b2d8c4a1e7
Revises: e4a1c7b3f9d6
Create Date: 2026-11-02 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f5b2d8c4a1e7"
down_revision: str | None = "e4a1c7b3f9d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partes_video",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("inicio_segundos", sa.Float(), nullable=False),
        sa.Column("fim_segundos", sa.Float(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("resumo", sa.Text(), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos_youtube.id"],
            name=op.f("fk_partes_video_video_id_videos_youtube"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partes_video")),
        sa.UniqueConstraint("video_id", "ordem", name="uq_partes_video_video_ordem"),
    )
    op.create_index(op.f("ix_partes_video_video_id"), "partes_video", ["video_id"], unique=False)

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE partes_video ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_partes_video_video_id"), table_name="partes_video")
    op.drop_table("partes_video")
