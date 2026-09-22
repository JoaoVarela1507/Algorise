from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

# Vale para desenvolvimento e para os testes; em produção a aplicação se recusa
# a subir com ele (ver `_conferir_segredo`).
SEGREDO_DE_DESENVOLVIMENTO = "inseguro-so-para-desenvolvimento"


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

    # O refresh token vive no Redis e expira sozinho. O prazo longo é o do
    # "manter-se conectado" da tela 5; sem marcar, vale uma semana.
    refresh_token_ttl: int = 60 * 60 * 24 * 7
    refresh_token_ttl_lembrar: int = 60 * 60 * 24 * 30

    # Assina os JWT. Em produção vem do ambiente, e a aplicação não sobe sem.
    jwt_secret: str = SEGREDO_DE_DESENVOLVIMENTO
    jwt_algoritmo: str = "HS256"

    # Access token curto porque ele não é consultado no Redis a cada request:
    # é esse prazo que limita quanto tempo um logout demora a valer de fato.
    access_token_ttl: int = 15 * 60

    # Credenciais do login social. Ficam em branco por padrão; com elas em
    # branco, as rotas do provedor respondem 503 em vez de quebrar.
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Para onde o callback do OAuth devolve o aluno, no frontend.
    oauth_retorno_frontend: str = "/auth/callback"

    # Validade do link de recuperação de senha.
    reset_senha_ttl: int = 30 * 60

    @model_validator(mode="after")
    def _conferir_segredo(self) -> "Settings":
        """Impede subir em produção sem um segredo próprio.

        Um JWT assinado com segredo público — ou vazio — é um token que qualquer
        um falsifica. Melhor não subir do que subir aberto.

        O `.env.example` traz `JWT_SECRET=` em branco, então vazio conta como
        "não definido": em desenvolvimento vira o segredo de desenvolvimento, em
        produção derruba o boot.
        """
        if not self.jwt_secret.strip():
            self.jwt_secret = SEGREDO_DE_DESENVOLVIMENTO

        if self.environment == "production" and self.jwt_secret == SEGREDO_DE_DESENVOLVIMENTO:
            raise ValueError(
                "Defina JWT_SECRET: em produção o segredo de desenvolvimento não é aceito"
            )
        return self


settings = Settings()
