"""anexos e resumo do chat

Revision ID: d6f2b9c5e1a4
Revises: c5e1a8b4d0f3
Create Date: 2026-11-03 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d6f2b9c5e1a4"
down_revision: str | None = "c5e1a8b4d0f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversas", sa.Column("resumo", sa.Text(), nullable=True))
    op.add_column("conversas", sa.Column("resumo_ate_id", sa.Integer(), nullable=True))

    op.create_table(
        "anexos_chat",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("mensagem_id", sa.Integer(), nullable=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column("arquivo", sa.String(length=100), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
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
            name=op.f("fk_anexos_chat_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mensagem_id"],
            ["mensagens_chat.id"],
            name=op.f("fk_anexos_chat_mensagem_id_mensagens_chat"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anexos_chat")),
    )
    op.create_index(op.f("ix_anexos_chat_usuario_id"), "anexos_chat", ["usuario_id"], unique=False)
    op.create_index(
        op.f("ix_anexos_chat_mensagem_id"), "anexos_chat", ["mensagem_id"], unique=False
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE anexos_chat ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_anexos_chat_mensagem_id"), table_name="anexos_chat")
    op.drop_index(op.f("ix_anexos_chat_usuario_id"), table_name="anexos_chat")
    op.drop_table("anexos_chat")
    op.drop_column("conversas", "resumo_ate_id")
    op.drop_column("conversas", "resumo")
