from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

# Segredo conhecido de propósito: serve para desenvolvimento e teste, e é
# justamente por ser conhecido que a API se recusa a subir em produção com ele.
SEGREDO_DESENVOLVIMENTO = "segredo-de-desenvolvimento-nao-use-em-producao"


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

    # Assina os JWT e o cookie de sessão do OAuth. Em produção precisa vir do
    # ambiente, com pelo menos 32 caracteres (ver `_segredos_de_producao`).
    jwt_secret: str = SEGREDO_DESENVOLVIMENTO
    jwt_algoritmo: str = "HS256"

    # O access token não é consultado no Redis a cada request, então o prazo curto
    # é o que limita o estrago de um token vazado ou de uma sessão já encerrada.
    access_token_ttl: int = 60 * 15

    # O refresh token vive no Redis e expira sozinho: 1 dia por padrão e 30 com
    # "manter-se conectado" marcado.
    refresh_token_ttl: int = 60 * 60 * 24
    refresh_token_ttl_estendido: int = 60 * 60 * 24 * 30

    # Link de "Esqueceu a senha?": uso único e prazo curto.
    redefinir_senha_ttl: int = 60 * 30

    # Credenciais dos apps OAuth. Em branco, o botão correspondente responde 503
    # em vez de a API deixar de subir: dá para desenvolver sem configurar os dois.
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Onde o backend recebe o callback do provedor. Precisa bater com o que foi
    # cadastrado no app OAuth do GitHub e do Google.
    api_url: str = "http://localhost:8000"

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def _segredo_em_branco(cls, valor: str | None) -> str:
        # `JWT_SECRET=` em branco no .env vale como "não definido".
        return valor or SEGREDO_DESENVOLVIMENTO

    @model_validator(mode="after")
    def _segredos_de_producao(self) -> "Settings":
        if self.environment == "production" and (
            self.jwt_secret == SEGREDO_DESENVOLVIMENTO or len(self.jwt_secret) < 32
        ):
            raise ValueError(
                "JWT_SECRET ausente ou fraco em produção: defina um segredo aleatório com "
                'pelo menos 32 caracteres (ex.: `python -c "import secrets; '
                'print(secrets.token_urlsafe(48))"`).'
            )
        return self


settings = Settings()
