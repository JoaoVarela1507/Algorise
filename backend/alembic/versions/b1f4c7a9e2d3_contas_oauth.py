"""contas oauth

Revision ID: b1f4c7a9e2d3
Revises: 69d2aaaacc82
Create Date: 2026-09-22 10:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1f4c7a9e2d3"
down_revision: str | None = "69d2aaaacc82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contas_oauth",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("provedor", sa.String(length=20), nullable=False),
        sa.Column("provedor_id", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_contas_oauth_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contas_oauth")),
        sa.UniqueConstraint("provedor", "provedor_id", name="uq_contas_oauth_provedor"),
    )
    op.create_index(
        op.f("ix_contas_oauth_usuario_id"), "contas_oauth", ["usuario_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_contas_oauth_usuario_id"), table_name="contas_oauth")
    op.drop_table("contas_oauth")
