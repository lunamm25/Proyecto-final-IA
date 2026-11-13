"""Fixtures compartidas: base de datos SQLite en memoria con todas las tablas."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings

# Los tests nunca leen el backend/.env real (tiene claves): se desactiva antes de importar la app.
Settings.model_config["env_file"] = None
get_settings.cache_clear()

import app.models  # noqa: E402, F401  (registra los modelos en Base.metadata)
from app.db import Base  # noqa: E402


@pytest.fixture
def engine_sqlite():
    """Engine SQLite en memoria con claves foráneas activas y todas las tablas creadas."""
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _activar_fk(conexion, _registro):
        conexion.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sesion(engine_sqlite) -> Iterator[Session]:
    """Sesión de base de datos para un test."""
    with sessionmaker(bind=engine_sqlite)() as session:
        yield session
