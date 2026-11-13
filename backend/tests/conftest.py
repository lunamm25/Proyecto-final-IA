"""Fixtures compartidas: base de datos SQLite en memoria con todas las tablas."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  (registra los modelos en Base.metadata)
from app.db import Base


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
