from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Algorise API"
    app_version: str = __version__
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"

    # Preenchidos pelo CI no build da imagem; em dev ficam como "unknown".
    git_commit: str = "unknown"
    build_time: str | None = None

    # O default serve para rodar fora do Docker; o compose injeta o host `db`.
    database_url: str = "postgresql+psycopg://algorise:algorise@localhost:5432/algorise"

    # Segundos de espera ao abrir conexão. Mantém o /ready respondendo rápido
    # quando o banco está fora.
    database_connect_timeout: int = 3

    # Mesmo raciocínio do database_url: o default é para rodar fora do Docker.
    redis_url: str = "redis://localhost:6379/0"

    # Timeout curto de propósito: o Redis é só cache, então esperar por ele é
    # pior do que ir no banco. Com o Redis fora, cada tentativa custa isso.
    redis_timeout: int = 2

    # Segundos de validade do cache. O catálogo de trilhas muda raramente; o
    # ranking, a cada XP ganho — e nele o TTL é só a rede de segurança, porque
    # a invalidação é explícita.
    cache_ttl_trilhas: int = 300
    cache_ttl_ranking: int = 60

    # Janela e teto do rate limit do chat, que custa chamada de IA por request.
    rate_limit_chat_requisicoes: int = 20
    rate_limit_chat_janela: int = 60

    # 30 dias: o refresh token vive no Redis e expira sozinho.
    refresh_token_ttl: int = 60 * 60 * 24 * 30


settings = Settings()
