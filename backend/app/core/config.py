from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Algorise API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
