"""onboarding e ementa

Revision ID: d4e9f2a7b3c5
Revises: c3d8e1f6a2b4
Create Date: 2026-10-27 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e9f2a7b3c5"
down_revision: str | None = "c3d8e1f6a2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `server_default` falso: o que já existe no banco foi digitado por aluno, e
    # só o seed marca como verificado.
    op.add_column(
        "instituicoes",
        sa.Column("verificada", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "cursos",
        sa.Column("verificado", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "usuarios",
        sa.Column("onboarding_concluido_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("ementas", sa.Column("nome_original", sa.String(length=255), nullable=True))
    op.add_column("ementas", sa.Column("tamanho_bytes", sa.Integer(), nullable=True))
    op.add_column("ementas", sa.Column("hash_sha256", sa.String(length=64), nullable=True))
    op.add_column("ementas", sa.Column("paginas", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_ementas_hash_sha256"), "ementas", ["hash_sha256"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ementas_hash_sha256"), table_name="ementas")
    op.drop_column("ementas", "paginas")
    op.drop_column("ementas", "hash_sha256")
    op.drop_column("ementas", "tamanho_bytes")
    op.drop_column("ementas", "nome_original")
    op.drop_column("usuarios", "onboarding_concluido_em")
    op.drop_column("cursos", "verificado")
    op.drop_column("instituicoes", "verificada")
