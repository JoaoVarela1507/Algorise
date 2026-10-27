"""Fixtures da suíte.

Duas decisões que valem para todos os testes:

- **banco em SQLite na memória, recriado por teste.** O CI já roda migrações
  contra o PostgreSQL de verdade (`alembic upgrade/downgrade/upgrade`), então o
  papel daqui é outro: ser rápido e isolado o bastante para ninguém precisar de
  Docker para rodar `pytest`. Onde o comportamento depende do Postgres, o teste
  diz isso no nome;
- **Redis falso.** O `fakeredis` implementa o que usamos (sorted set, pipeline,
  `getdel`, TTL), e o teste que precisa do Redis fora usa a fixture
  `redis_fora`, que faz todo comando estourar.
"""

from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from redis import ConnectionError as RedisConnectionError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import redis as nucleo_redis
from app.core.database import get_db
from app.main import app
from app.models import Base, Trilha, Usuario
from app.services import auth as servico_auth

SENHA_VALIDA = "Trilha-Boa-2026"


@pytest.fixture
def redis_falso() -> Iterator[fakeredis.FakeRedis]:
    """Substitui o cliente real. Cada teste começa com o Redis vazio."""
    falso = fakeredis.FakeRedis(decode_responses=True)
    original = nucleo_redis.cliente
    nucleo_redis.cliente = falso
    try:
        yield falso
    finally:
        nucleo_redis.cliente = original


@pytest.fixture
def redis_fora(redis_falso: fakeredis.FakeRedis) -> Iterator[None]:
    """Redis desligado: todo comando estoura, como um container parado.

    Depende de `redis_falso` para restaurar o cliente original no fim.
    """

    class Desligado:
        def __getattr__(self, _nome: str):
            def estourar(*_args: object, **_kwargs: object) -> None:
                raise RedisConnectionError("Redis fora (simulado no teste)")

            return estourar

    nucleo_redis.cliente = Desligado()
    yield


@pytest.fixture
def sessao_factory() -> Iterator[sessionmaker[Session]]:
    """Banco novo por teste.

    `StaticPool` com `sqlite://` mantém todas as conexões na mesma base em
    memória — sem isso, cada conexão abriria um banco vazio e a aplicação não
    enxergaria o que o teste inseriu.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db(sessao_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Sessão para o teste montar e conferir dados direto no banco."""
    with sessao_factory() as sessao:
        yield sessao


@pytest.fixture
def cliente(
    sessao_factory: sessionmaker[Session], redis_falso: fakeredis.FakeRedis
) -> Iterator[TestClient]:
    """Cliente HTTP da aplicação, com o banco e o Redis do teste.

    `raise_server_exceptions=False` para o teste ver o 500 que o handler
    devolve, em vez de receber a exceção original.
    """

    def get_db_de_teste() -> Iterator[Session]:
        with sessao_factory() as sessao:
            yield sessao

    app.dependency_overrides[get_db] = get_db_de_teste
    try:
        with TestClient(app, raise_server_exceptions=False) as cliente_http:
            yield cliente_http
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def usuario(db: Session) -> Usuario:
    """Aluno cadastrado, com senha conhecida (`SENHA_VALIDA`)."""
    return servico_auth.registrar(
        db,
        email="ana@ufrpe.br",
        senha=SENHA_VALIDA,
        username="ana",
        nome_exibicao="Ana Lima",
    )


@pytest.fixture
def sessao_aberta(cliente: TestClient, usuario: Usuario) -> dict[str, str]:
    """Par de tokens de um aluno já logado."""
    resposta = cliente.post(
        "/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA_VALIDA}
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.fixture
def autenticado(sessao_aberta: dict[str, str]) -> dict[str, str]:
    """Header pronto para as rotas privadas."""
    return {"Authorization": f"Bearer {sessao_aberta['access_token']}"}


@pytest.fixture
def trilha(db: Session) -> Trilha:
    trilha_publicada = Trilha(
        slug="introducao-python",
        nome="Introdução a Python",
        disciplina="Algoritmos",
        periodo=1,
        publicada=True,
    )
    db.add(trilha_publicada)
    db.commit()
    return trilha_publicada
