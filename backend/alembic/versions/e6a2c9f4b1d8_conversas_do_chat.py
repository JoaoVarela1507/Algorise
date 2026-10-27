"""conversas do chat

Revision ID: e6a2c9f4b1d8
Revises: d4e9f2a7b3c5
Create Date: 2026-10-27 02:48:14.199941
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6a2c9f4b1d8"
down_revision: str | None = "d4e9f2a7b3c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

papel = sa.Enum("usuario", "assistente", name="papelmensagem")


def upgrade() -> None:
    op.create_table(
        "conversas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=120), nullable=False),
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
            name=op.f("fk_conversas_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversas")),
    )
    op.create_index(op.f("ix_conversas_usuario_id"), "conversas", ["usuario_id"], unique=False)
    op.create_table(
        "mensagens_chat",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversa_id", sa.Integer(), nullable=False),
        sa.Column("papel", papel, nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("incompleta", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["conversa_id"],
            ["conversas.id"],
            name=op.f("fk_mensagens_chat_conversa_id_conversas"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mensagens_chat")),
    )
    op.create_index(
        op.f("ix_mensagens_chat_conversa_id"), "mensagens_chat", ["conversa_id"], unique=False
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5): no Supabase, sem isso
    # as conversas dos alunos ficariam legíveis pela chave anon.
    op.execute("ALTER TABLE conversas ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE mensagens_chat ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_mensagens_chat_conversa_id"), table_name="mensagens_chat")
    op.drop_table("mensagens_chat")
    op.drop_index(op.f("ix_conversas_usuario_id"), table_name="conversas")
    op.drop_table("conversas")
    # O `drop_table` não leva o tipo junto, e o próximo `upgrade` esbarraria
    # nele já existindo.
    papel.drop(op.get_bind(), checkfirst=True)
