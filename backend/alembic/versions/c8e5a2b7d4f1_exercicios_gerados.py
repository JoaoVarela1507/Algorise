"""exercícios gerados

Revision ID: c8e5a2b7d4f1
Revises: b7d4f1a6c3e9
Create Date: 2026-11-03 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c8e5a2b7d4f1"
down_revision: str | None = "b7d4f1a6c3e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status_geracao = sa.Enum("gerando", "pronto", "sem_conteudo", "falhou", name="statusgeracao")
# Já existe desde o schema inicial (`usuarios.nivel_experiencia`).
nivel_experiencia = postgresql.ENUM(
    "baixo", "medio", "alto", name="nivelexperiencia", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "exercicios_gerados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("modulo_id", sa.Integer(), nullable=False),
        sa.Column("nivel", nivel_experiencia, nullable=False),
        sa.Column("status", status_geracao, nullable=False),
        sa.Column("exercicios", sa.JSON(), nullable=False),
        sa.Column("erro", sa.Text(), nullable=True),
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
            name=op.f("fk_exercicios_gerados_modulo_id_modulos"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercicios_gerados")),
        sa.UniqueConstraint("modulo_id", "nivel", name="uq_exercicios_gerados_modulo_nivel"),
    )
    op.create_index(
        op.f("ix_exercicios_gerados_modulo_id"), "exercicios_gerados", ["modulo_id"], unique=False
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE exercicios_gerados ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_exercicios_gerados_modulo_id"), table_name="exercicios_gerados")
    op.drop_table("exercicios_gerados")
    status_geracao.drop(op.get_bind(), checkfirst=True)
