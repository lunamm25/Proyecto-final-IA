"""Pruebas de configuración (Settings) y de la conexión perezosa a la BD."""

import pytest

from app.config import Settings, get_settings
from app.db import BaseDatosNoConfiguradaError, get_engine, normalizar_database_url

VARIABLES = [
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_JWT_SECRET",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_TEMPERATURE",
    "GEMINI_API_KEY",
    "OPENAI_COMPAT_MODELOS",
    "FRONTEND_URL",
]


@pytest.fixture
def entorno_limpio(monkeypatch):
    """Quita las variables del entorno para probar los valores por defecto."""
    for nombre in VARIABLES:
        monkeypatch.delenv(nombre, raising=False)
    return monkeypatch


def test_settings_defaults(entorno_limpio):
    s = Settings(_env_file=None)
    assert s.database_url == ""
    assert s.supabase_url == ""
    assert s.supabase_service_key == ""
    assert s.supabase_jwt_secret == ""
    assert s.gemini_api_key == ""
    assert s.llm_provider == "gemini"
    assert s.llm_model == "gemini-3.5-flash-lite"
    assert s.openai_compat_modelos == ""
    assert s.llm_temperature == 0.1
    assert s.frontend_url == "http://localhost:3000"


def test_settings_lee_variables_de_entorno(entorno_limpio):
    entorno_limpio.setenv("DATABASE_URL", "postgresql://u:p@host:5432/postgres")
    entorno_limpio.setenv("LLM_TEMPERATURE", "0.2")
    entorno_limpio.setenv("FRONTEND_URL", "https://mi-app.vercel.app")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql://u:p@host:5432/postgres"
    assert s.llm_temperature == 0.2
    assert s.frontend_url == "https://mi-app.vercel.app"


def test_settings_lee_archivo_env(entorno_limpio, tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text("SUPABASE_URL=https://abc.supabase.co\n", encoding="utf-8")
    assert Settings(_env_file=archivo).supabase_url == "https://abc.supabase.co"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("  postgresql://u:p@h/db  ", "postgresql+psycopg://u:p@h/db"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_normalizar_database_url(entrada, esperado):
    assert normalizar_database_url(entrada) == esperado


def test_engine_sin_database_url_da_error_claro(entorno_limpio, tmp_path):
    entorno_limpio.chdir(tmp_path)  # carpeta sin .env
    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        with pytest.raises(BaseDatosNoConfiguradaError, match="DATABASE_URL"):
            get_engine()
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()


def test_importar_app_no_requiere_bd():
    from fastapi.testclient import TestClient

    from app.main import app

    assert TestClient(app).get("/api/salud").status_code == 200
