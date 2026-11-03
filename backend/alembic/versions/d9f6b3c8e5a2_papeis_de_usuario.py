"""papéis de usuário

Revision ID: d9f6b3c8e5a2
Revises: c8e5a2b7d4f1
Create Date: 2026-11-03 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d9f6b3c8e5a2"
down_revision: str | None = "c8e5a2b7d4f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

papel_usuario = sa.Enum("aluno", "autor", "admin", name="papelusuario")


def upgrade() -> None:
    papel_usuario.create(op.get_bind(), checkfirst=True)
    # Todo mundo que já existe é aluno; autor e admin se promovem pela linha de
    # comando (`python -m app.tarefas.papeis`).
    op.add_column(
        "usuarios",
        sa.Column("papel", papel_usuario, server_default="aluno", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "papel")
    papel_usuario.drop(op.get_bind(), checkfirst=True)
