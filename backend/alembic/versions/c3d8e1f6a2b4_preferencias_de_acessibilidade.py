"""preferencias de acessibilidade

Revision ID: c3d8e1f6a2b4
Revises: b5cf497366ef
Create Date: 2026-10-26 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d8e1f6a2b4"
down_revision: str | None = "b5cf497366ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

tamanho_fonte = sa.Enum("normal", "alta", name="tamanhofonte")


def upgrade() -> None:
    tamanho_fonte.create(op.get_bind(), checkfirst=True)
    # `server_default` para as contas que já existem entrarem com o padrão, em
    # vez de a migração falhar no NOT NULL.
    op.add_column(
        "usuarios",
        sa.Column("tamanho_fonte", tamanho_fonte, server_default="normal", nullable=False),
    )
    op.add_column(
        "usuarios",
        sa.Column("alto_contraste", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "usuarios",
        sa.Column("reduzir_animacoes", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "reduzir_animacoes")
    op.drop_column("usuarios", "alto_contraste")
    op.drop_column("usuarios", "tamanho_fonte")
    # O `drop_column` não leva o tipo junto: sem isto, o próximo `upgrade`
    # tropeça no ENUM que ficou para trás.
    tamanho_fonte.drop(op.get_bind(), checkfirst=True)
