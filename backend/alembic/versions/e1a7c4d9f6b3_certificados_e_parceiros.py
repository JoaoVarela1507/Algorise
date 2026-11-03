"""certificados e parceiros

Revision ID: e1a7c4d9f6b3
Revises: d9f6b3c8e5a2
Create Date: 2026-11-03 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1a7c4d9f6b3"
down_revision: str | None = "d9f6b3c8e5a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parceiros",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("site", sa.String(length=300), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parceiros")),
        sa.UniqueConstraint("nome", name=op.f("uq_parceiros_nome")),
    )

    op.add_column("trilhas", sa.Column("parceiro_id", sa.Integer(), nullable=True))
    op.add_column("trilhas", sa.Column("carga_horaria", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_trilhas_parceiro_id_parceiros"),
        "trilhas",
        "parceiros",
        ["parceiro_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_trilhas_parceiro_id"), "trilhas", ["parceiro_id"], unique=False)

    # O que o certificado disse no dia da emissão (ver `Certificado`).
    for coluna, tipo in (
        ("nome_aluno", sa.String(length=200)),
        ("nome_trilha", sa.String(length=200)),
        ("disciplina", sa.String(length=200)),
        ("carga_horaria", sa.Integer()),
    ):
        op.add_column("certificados", sa.Column(coluna, tipo, nullable=True))
    op.create_unique_constraint(
        "uq_certificados_usuario_trilha", "certificados", ["usuario_id", "trilha_id"]
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE parceiros ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_constraint("uq_certificados_usuario_trilha", "certificados", type_="unique")
    for coluna in ("carga_horaria", "disciplina", "nome_trilha", "nome_aluno"):
        op.drop_column("certificados", coluna)
    op.drop_index(op.f("ix_trilhas_parceiro_id"), table_name="trilhas")
    op.drop_constraint(op.f("fk_trilhas_parceiro_id_parceiros"), "trilhas", type_="foreignkey")
    op.drop_column("trilhas", "carga_horaria")
    op.drop_column("trilhas", "parceiro_id")
    op.drop_table("parceiros")
