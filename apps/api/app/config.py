from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PSST_", extra="ignore")

    database_url: str = "postgresql+asyncpg://psst:psst@localhost:5433/psst"
    web_origin: str = "http://localhost:3000"
    # En producción (HTTPS) tiene que ser True para que la cookie solo viaje cifrada.
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
