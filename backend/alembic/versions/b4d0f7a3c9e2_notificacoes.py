"""notificações

Revision ID: b4d0f7a3c9e2
Revises: a3c9e6f2b8d1
Create Date: 2026-11-03 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4d0f7a3c9e2"
down_revision: str | None = "a3c9e6f2b8d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notificacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("titulo", sa.String(length=120), nullable=False),
        sa.Column("mensagem", sa.String(length=300), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=False),
        sa.Column("lida_em", sa.DateTime(timezone=True), nullable=True),
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
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_notificacoes_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notificacoes")),
    )
    op.create_index(
        "ix_notificacoes_usuario_lida", "notificacoes", ["usuario_id", "lida_em"], unique=False
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE notificacoes ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_notificacoes_usuario_lida", table_name="notificacoes")
    op.drop_table("notificacoes")
