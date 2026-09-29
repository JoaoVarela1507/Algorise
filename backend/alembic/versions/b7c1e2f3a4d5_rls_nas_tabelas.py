"""rls nas tabelas

Liga o Row Level Security em todas as tabelas, sem nenhuma policy.

No Supabase o schema `public` é exposto pela Data API (PostgREST) a quem tiver a
chave `anon`, que é pública por definição. Sem RLS, `usuarios` — com
`senha_hash` — ficaria legível por ela. Com RLS e zero policies, os papéis da
Data API (`anon`, `authenticated`) não enxergam nenhuma linha.

O backend não é afetado: conecta como dono das tabelas, e o dono ignora RLS
(sem `FORCE ROW LEVEL SECURITY`). Num PostgreSQL comum, como o do Docker, a
migração é inócua pelo mesmo motivo.

Tabela nova precisa entrar na mesma regra: ligar o RLS na migração que a cria.

Revision ID: b7c1e2f3a4d5
Revises: b1f4c7a9e2d3
Create Date: 2026-09-29 17:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b7c1e2f3a4d5"
down_revision: str | None = "b1f4c7a9e2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELAS = (
    "alembic_version",
    "atividades",
    "certificados",
    "contas_oauth",
    "cursos",
    "ementas",
    "instituicoes",
    "modulos",
    "progresso_usuario",
    "respostas_usuario",
    "streaks",
    "trilhas",
    "usuarios",
    "xp_eventos",
)


def upgrade() -> None:
    for tabela in TABELAS:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for tabela in TABELAS:
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY")
