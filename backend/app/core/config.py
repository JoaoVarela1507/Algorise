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


settings = Settings()
