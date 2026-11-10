from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PSST_", extra="ignore")

    database_url: str = "postgresql+asyncpg://psst:psst@localhost:5433/psst"
    web_origin: str = "http://localhost:3000"
    # En producción (HTTPS) tiene que ser True para que la cookie solo viaje cifrada.
    cookie_secure: bool = False
    # Claves VAPID para las push (ver scripts/gen_vapid.py). Vacías = sin avisos.
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    # Contacto que ven los servicios de push si algo va mal con nuestros envíos.
    vapid_subject: str = "mailto:hola@example.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
