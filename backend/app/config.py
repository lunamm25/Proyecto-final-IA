"""Configuración de la aplicación leída desde variables de entorno y `.env`."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno del backend (con valores por defecto seguros)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.5-flash-lite"
    llm_temperature: float = 0.1
    openai_compat_base_url: str = ""
    openai_compat_api_key: str = ""
    openai_compat_modelos: str = ""
    gemini_api_key: str = ""
    frontend_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada (una sola instancia por proceso)."""
    return Settings()
