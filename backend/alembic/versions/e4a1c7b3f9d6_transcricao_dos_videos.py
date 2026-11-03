"""transcrição dos vídeos

Revision ID: e4a1c7b3f9d6
Revises: d3f9b6a2e8c5
Create Date: 2026-11-02 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4a1c7b3f9d6"
down_revision: str | None = "d3f9b6a2e8c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A transcrição de um vídeo do YouTube ainda sem módulo (#208).
    op.add_column("vault_documentos", sa.Column("video_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_vault_documentos_video_id"), "vault_documentos", ["video_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_vault_documentos_video_id_videos_youtube"),
        "vault_documentos",
        "videos_youtube",
        ["video_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Onde o trecho termina no vídeo, para a busca recortar um intervalo.
    op.add_column("vault_trechos", sa.Column("fim_segundos", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("vault_trechos", "fim_segundos")
    op.drop_constraint(
        op.f("fk_vault_documentos_video_id_videos_youtube"), "vault_documentos", type_="foreignkey"
    )
    op.drop_index(op.f("ix_vault_documentos_video_id"), table_name="vault_documentos")
    op.drop_column("vault_documentos", "video_id")
