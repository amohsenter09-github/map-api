from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "map-api-fastapi"
    log_level: str = "INFO"

    open_meteo_geocoding_base_url: str = "https://geocoding-api.open-meteo.com/v1"
    http_timeout_seconds: float = 10.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
