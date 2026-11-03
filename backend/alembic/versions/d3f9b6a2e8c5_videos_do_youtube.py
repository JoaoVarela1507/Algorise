"""videos do youtube

Revision ID: d3f9b6a2e8c5
Revises: c2e8a5f1d7b4
Create Date: 2026-11-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d3f9b6a2e8c5"
down_revision: str | None = "c2e8a5f1d7b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status_video = sa.Enum("aguardando", "transcrevendo", "transcrito", "falhou", name="statusvideo")


def _carimbos() -> list[sa.Column]:
    return [
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "videos_youtube",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("youtube_id", sa.String(length=20), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("canal", sa.String(length=200), nullable=True),
        sa.Column("duracao_segundos", sa.Integer(), nullable=True),
        sa.Column("playlist_id", sa.String(length=64), nullable=True),
        sa.Column("posicao", sa.Integer(), nullable=True),
        sa.Column("status", status_video, nullable=False),
        sa.Column("erro", sa.Text(), nullable=True),
        *_carimbos(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_videos_youtube")),
        sa.UniqueConstraint("youtube_id", name=op.f("uq_videos_youtube_youtube_id")),
    )
    op.create_index(op.f("ix_videos_youtube_status"), "videos_youtube", ["status"], unique=False)

    op.create_table(
        "video_lacunas",
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("lacuna_id", sa.Integer(), nullable=False),
        sa.Column("distancia", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos_youtube.id"],
            name=op.f("fk_video_lacunas_video_id_videos_youtube"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lacuna_id"],
            ["lacunas.id"],
            name=op.f("fk_video_lacunas_lacuna_id_lacunas"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("video_id", "lacuna_id", name=op.f("pk_video_lacunas")),
    )
    op.create_index(
        op.f("ix_video_lacunas_lacuna_id"), "video_lacunas", ["lacuna_id"], unique=False
    )

    op.create_table(
        "buscas_youtube",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chave", sa.String(length=500), nullable=False),
        sa.Column("resposta", sa.JSON(), nullable=False),
        *_carimbos(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buscas_youtube")),
        sa.UniqueConstraint("chave", name=op.f("uq_buscas_youtube_chave")),
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    for tabela in ("videos_youtube", "video_lacunas", "buscas_youtube"):
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("buscas_youtube")
    op.drop_index(op.f("ix_video_lacunas_lacuna_id"), table_name="video_lacunas")
    op.drop_table("video_lacunas")
    op.drop_index(op.f("ix_videos_youtube_status"), table_name="videos_youtube")
    op.drop_table("videos_youtube")
    status_video.drop(op.get_bind(), checkfirst=True)
