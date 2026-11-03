"""grupos e busca do chat

Revision ID: a3c9e6f2b8d1
Revises: f2b8d5e1a7c4
Create Date: 2026-11-04 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a3c9e6f2b8d1"
down_revision: str | None = "f2b8d5e1a7c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grupos_chat",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=80), nullable=False),
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
            name=op.f("fk_grupos_chat_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grupos_chat")),
    )
    op.create_index(op.f("ix_grupos_chat_usuario_id"), "grupos_chat", ["usuario_id"], unique=False)

    op.add_column(
        "conversas",
        sa.Column("arquivada", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("conversas", sa.Column("grupo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_conversas_grupo_id_grupos_chat"),
        "conversas",
        "grupos_chat",
        ["grupo_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_conversas_grupo_id"), "conversas", ["grupo_id"], unique=False)

    # Busca por palavra-chave no histórico, em português (#33).
    op.execute(
        "CREATE INDEX ix_mensagens_chat_conteudo_busca ON mensagens_chat "
        "USING gin (to_tsvector('portuguese', conteudo))"
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE grupos_chat ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_mensagens_chat_conteudo_busca")
    op.drop_index(op.f("ix_conversas_grupo_id"), table_name="conversas")
    op.drop_constraint(op.f("fk_conversas_grupo_id_grupos_chat"), "conversas", type_="foreignkey")
    op.drop_column("conversas", "grupo_id")
    op.drop_column("conversas", "arquivada")
    op.drop_index(op.f("ix_grupos_chat_usuario_id"), table_name="grupos_chat")
    op.drop_table("grupos_chat")
