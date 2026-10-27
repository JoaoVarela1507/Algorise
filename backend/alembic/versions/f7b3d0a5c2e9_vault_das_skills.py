"""vault das skills

Revision ID: f7b3d0a5c2e9
Revises: e6a2c9f4b1d8
Create Date: 2026-10-27 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "f7b3d0a5c2e9"
down_revision: str | None = "e6a2c9f4b1d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

origem = sa.Enum("transcricao", "prompt", name="origemvault")


def upgrade() -> None:
    # No Supabase a extensão já vem disponível; no compose e no CI, a imagem
    # `pgvector/pgvector` traz o binário.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "vault_documentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("origem", origem, nullable=False),
        sa.Column("chave", sa.String(length=120), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("modulo_id", sa.Integer(), nullable=True),
        sa.Column("skill", sa.String(length=80), nullable=True),
        sa.Column("hash_conteudo", sa.String(length=64), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
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
            ["modulo_id"],
            ["modulos.id"],
            name=op.f("fk_vault_documentos_modulo_id_modulos"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vault_documentos")),
        sa.UniqueConstraint("chave", name=op.f("uq_vault_documentos_chave")),
    )
    op.create_index(
        op.f("ix_vault_documentos_modulo_id"), "vault_documentos", ["modulo_id"], unique=False
    )
    op.create_table(
        "vault_trechos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("inicio_segundos", sa.Float(), nullable=True),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.ForeignKeyConstraint(
            ["documento_id"],
            ["vault_documentos.id"],
            name=op.f("fk_vault_trechos_documento_id_vault_documentos"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vault_trechos")),
        sa.UniqueConstraint("documento_id", "ordem", name="uq_vault_trechos_documento_ordem"),
    )
    op.create_index(
        op.f("ix_vault_trechos_documento_id"), "vault_trechos", ["documento_id"], unique=False
    )
    op.create_index(
        "ix_vault_trechos_embedding",
        "vault_trechos",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE vault_documentos ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE vault_trechos ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_vault_trechos_embedding", table_name="vault_trechos")
    op.drop_index(op.f("ix_vault_trechos_documento_id"), table_name="vault_trechos")
    op.drop_table("vault_trechos")
    op.drop_index(op.f("ix_vault_documentos_modulo_id"), table_name="vault_documentos")
    op.drop_table("vault_documentos")
    # O `drop_table` não leva o tipo junto, e o próximo `upgrade` esbarraria
    # nele já existindo.
    origem.drop(op.get_bind(), checkfirst=True)
    # A extensão fica: no Supabase ela pode servir a outras tabelas, e criá-la
    # de novo no próximo upgrade não custa nada.
