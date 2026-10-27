"""assuntos e lacunas da ementa

Revision ID: a8c4e1d6f3b2
Revises: f7b3d0a5c2e9
Create Date: 2026-10-27 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a8c4e1d6f3b2"
down_revision: str | None = "f7b3d0a5c2e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status_lacuna = sa.Enum("pendente", "em_preparacao", "coberta", "sem_conteudo", name="statuslacuna")
status_assuntos = sa.Enum("pendente", "processando", "prontos", "falhou", name="statusassuntos")


def upgrade() -> None:
    # O texto dos módulos do catálogo entra no vault (#38).
    op.execute("ALTER TYPE origemvault ADD VALUE IF NOT EXISTS 'modulo'")

    op.create_table(
        "lacunas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chave", sa.String(length=520), nullable=False),
        sa.Column("disciplina", sa.String(length=200), nullable=False),
        sa.Column("assunto", sa.String(length=300), nullable=False),
        sa.Column("status", status_lacuna, nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lacunas")),
        sa.UniqueConstraint("chave", name=op.f("uq_lacunas_chave")),
    )
    op.create_index(op.f("ix_lacunas_status"), "lacunas", ["status"], unique=False)

    op.create_table(
        "ementa_disciplinas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ementa_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("periodo", sa.Integer(), nullable=True),
        sa.Column("carga_horaria", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ementa_id"],
            ["ementas.id"],
            name=op.f("fk_ementa_disciplinas_ementa_id_ementas"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ementa_disciplinas")),
        sa.UniqueConstraint("ementa_id", "ordem", name="uq_ementa_disciplinas_ementa_ordem"),
    )
    op.create_index(
        op.f("ix_ementa_disciplinas_ementa_id"), "ementa_disciplinas", ["ementa_id"], unique=False
    )

    op.create_table(
        "ementa_assuntos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("disciplina_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("texto", sa.String(length=300), nullable=False),
        sa.Column("modulo_id", sa.Integer(), nullable=True),
        sa.Column("lacuna_id", sa.Integer(), nullable=True),
        sa.Column("distancia", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["disciplina_id"],
            ["ementa_disciplinas.id"],
            name=op.f("fk_ementa_assuntos_disciplina_id_ementa_disciplinas"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lacuna_id"],
            ["lacunas.id"],
            name=op.f("fk_ementa_assuntos_lacuna_id_lacunas"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["modulo_id"],
            ["modulos.id"],
            name=op.f("fk_ementa_assuntos_modulo_id_modulos"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ementa_assuntos")),
        sa.UniqueConstraint("disciplina_id", "ordem", name="uq_ementa_assuntos_disciplina_ordem"),
    )
    for coluna in ("disciplina_id", "lacuna_id", "modulo_id"):
        op.create_index(
            op.f(f"ix_ementa_assuntos_{coluna}"), "ementa_assuntos", [coluna], unique=False
        )

    # As ementas já lidas ficam `pendente`: a leitura dos assuntos roda quando
    # o aluno pedir de novo (`POST /ementas/{id}/assuntos`).
    status_assuntos.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "ementas",
        sa.Column(
            "status_assuntos", status_assuntos, server_default="pendente", nullable=False
        ),
    )
    op.add_column("ementas", sa.Column("erro_assuntos", sa.Text(), nullable=True))

    # Toda tabela nova entra com RLS (ver b7c1e2f3a4d5).
    for tabela in ("lacunas", "ementa_disciplinas", "ementa_assuntos"):
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_column("ementas", "erro_assuntos")
    op.drop_column("ementas", "status_assuntos")
    for coluna in ("modulo_id", "lacuna_id", "disciplina_id"):
        op.drop_index(op.f(f"ix_ementa_assuntos_{coluna}"), table_name="ementa_assuntos")
    op.drop_table("ementa_assuntos")
    op.drop_index(op.f("ix_ementa_disciplinas_ementa_id"), table_name="ementa_disciplinas")
    op.drop_table("ementa_disciplinas")
    op.drop_index(op.f("ix_lacunas_status"), table_name="lacunas")
    op.drop_table("lacunas")
    status_assuntos.drop(op.get_bind(), checkfirst=True)
    status_lacuna.drop(op.get_bind(), checkfirst=True)

    # O PostgreSQL não remove valor de enum: o tipo é recriado sem o `modulo`,
    # e os documentos dele saem antes (o registro refaz tudo num upgrade).
    op.execute("DELETE FROM vault_documentos WHERE origem = 'modulo'")
    op.execute("ALTER TYPE origemvault RENAME TO origemvault_antigo")
    op.execute("CREATE TYPE origemvault AS ENUM ('transcricao', 'prompt')")
    op.execute(
        "ALTER TABLE vault_documentos ALTER COLUMN origem "
        "TYPE origemvault USING origem::text::origemvault"
    )
    op.execute("DROP TYPE origemvault_antigo")
