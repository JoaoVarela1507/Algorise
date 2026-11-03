"""módulos de vídeos

Revision ID: b7d4f1a6c3e9
Revises: a6c3e9d5b2f8
Create Date: 2026-11-02 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7d4f1a6c3e9"
down_revision: str | None = "a6c3e9d5b2f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

origem_modulo = sa.Enum("manual", "youtube", name="origemmodulo")


def upgrade() -> None:
    origem_modulo.create(op.get_bind(), checkfirst=True)
    op.add_column("modulos", sa.Column("inicio_segundos", sa.Float(), nullable=True))
    op.add_column("modulos", sa.Column("fim_segundos", sa.Float(), nullable=True))
    # Os módulos que já existem vieram do seed: `manual`.
    op.add_column(
        "modulos", sa.Column("origem", origem_modulo, server_default="manual", nullable=False)
    )
    op.add_column("modulos", sa.Column("parte_video_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_modulos_parte_video_id_partes_video"),
        "modulos",
        "partes_video",
        ["parte_video_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        op.f("uq_modulos_parte_video_id"), "modulos", ["parte_video_id"]
    )

    op.add_column("lacunas", sa.Column("modulo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_lacunas_modulo_id_modulos"),
        "lacunas",
        "modulos",
        ["modulo_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_lacunas_modulo_id"), "lacunas", ["modulo_id"], unique=False)

    op.create_table(
        "reportes_modulo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("modulo_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
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
            name=op.f("fk_reportes_modulo_modulo_id_modulos"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_reportes_modulo_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reportes_modulo")),
        sa.UniqueConstraint(
            "modulo_id", "usuario_id", name="uq_reportes_modulo_modulo_usuario"
        ),
    )
    op.create_index(
        op.f("ix_reportes_modulo_modulo_id"), "reportes_modulo", ["modulo_id"], unique=False
    )

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    op.execute("ALTER TABLE reportes_modulo ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_reportes_modulo_modulo_id"), table_name="reportes_modulo")
    op.drop_table("reportes_modulo")
    op.drop_index(op.f("ix_lacunas_modulo_id"), table_name="lacunas")
    op.drop_constraint(op.f("fk_lacunas_modulo_id_modulos"), "lacunas", type_="foreignkey")
    op.drop_column("lacunas", "modulo_id")
    op.drop_constraint(op.f("uq_modulos_parte_video_id"), "modulos", type_="unique")
    op.drop_constraint(
        op.f("fk_modulos_parte_video_id_partes_video"), "modulos", type_="foreignkey"
    )
    for coluna in ("parte_video_id", "origem", "fim_segundos", "inicio_segundos"):
        op.drop_column("modulos", coluna)
    origem_modulo.drop(op.get_bind(), checkfirst=True)
