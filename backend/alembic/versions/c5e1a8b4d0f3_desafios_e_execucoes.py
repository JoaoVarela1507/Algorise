"""desafios e execuções

Revision ID: c5e1a8b4d0f3
Revises: a3c9e6f2b8d1
Create Date: 2026-11-03 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c5e1a8b4d0f3"
down_revision: str | None = "a3c9e6f2b8d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPS = (
    ("criado_em", sa.DateTime(timezone=True)),
    ("atualizado_em", sa.DateTime(timezone=True)),
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(nome, tipo, server_default=sa.text("now()"), nullable=False)
        for nome, tipo in _TIMESTAMPS
    ]


def upgrade() -> None:
    op.create_table(
        "casos_de_teste",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("atividade_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("entrada", sa.Text(), nullable=False),
        sa.Column("saida_esperada", sa.Text(), nullable=False),
        sa.Column("publico", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["atividade_id"],
            ["atividades.id"],
            name=op.f("fk_casos_de_teste_atividade_id_atividades"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_casos_de_teste")),
    )
    op.create_index(
        op.f("ix_casos_de_teste_atividade_id"), "casos_de_teste", ["atividade_id"], unique=False
    )

    status = sa.Enum("na_fila", "executando", "concluida", "falhou", name="statusexecucao")
    op.create_table(
        "execucoes",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("atividade_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("stdout", sa.Text(), nullable=False),
        sa.Column("stderr", sa.Text(), nullable=False),
        sa.Column("casos", sa.JSON(), nullable=False),
        sa.Column("aprovada", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("erro", sa.String(length=300), nullable=True),
        sa.Column("terminada_em", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_execucoes_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["atividade_id"],
            ["atividades.id"],
            name=op.f("fk_execucoes_atividade_id_atividades"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_execucoes")),
    )
    op.create_index(
        "ix_execucoes_usuario_atividade", "execucoes", ["usuario_id", "atividade_id"], unique=False
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE casos_de_teste ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE execucoes ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_execucoes_usuario_atividade", table_name="execucoes")
    op.drop_table("execucoes")
    sa.Enum(name="statusexecucao").drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f("ix_casos_de_teste_atividade_id"), table_name="casos_de_teste")
    op.drop_table("casos_de_teste")
