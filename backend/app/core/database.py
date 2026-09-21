"""Conexão com o PostgreSQL: engine, sessão por request e metadata."""

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Sem uma convenção explícita, o PostgreSQL nomeia as constraints sozinho e o
# Alembic gera migrações que não sabem desfazer. Isso precisa existir antes da
# primeira migração: mudar depois exige renomear tudo à mão.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

# `pool_pre_ping` descarta conexões mortas — o container do banco pode reiniciar
# sem a API perceber.
#
# `connect_timeout` existe para o /ready: sem ele, com o banco fora, a tentativa
# de conexão fica pendurada no timeout de TCP do sistema e o endpoint nunca
# responde — que é justamente quando ele mais importa.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": settings.database_connect_timeout},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """Dependência do FastAPI: uma sessão por request, sempre fechada no fim."""
    with SessionLocal() as sessao:
        yield sessao
