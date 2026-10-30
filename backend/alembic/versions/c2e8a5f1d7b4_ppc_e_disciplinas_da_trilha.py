"""ppc e disciplinas da trilha

Revision ID: c2e8a5f1d7b4
Revises: b9d5f2e7a4c3
Create Date: 2026-10-29 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2e8a5f1d7b4"
down_revision: str | None = "b9d5f2e7a4c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # O trecho do PDF lido: no PPC, só o ementário.
    op.add_column("ementas", sa.Column("pagina_inicial", sa.Integer(), nullable=True))
    op.add_column("ementas", sa.Column("pagina_final", sa.Integer(), nullable=True))

    op.add_column(
        "ementa_disciplinas",
        sa.Column("na_trilha", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # Até aqui toda disciplina lida entrava na trilha guiada: as que já existem
    # continuam nela, para nenhuma trilha confirmada ficar vazia.
    op.execute("UPDATE ementa_disciplinas SET na_trilha = true")


def downgrade() -> None:
    op.drop_column("ementa_disciplinas", "na_trilha")
    op.drop_column("ementas", "pagina_final")
    op.drop_column("ementas", "pagina_inicial")
