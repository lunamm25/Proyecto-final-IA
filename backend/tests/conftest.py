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


@pytest.fixture
def fabrica_api():
    """SQLite en memoria compartida entre hilos, con FK activas, perfiles y cohortes 1 y 2."""
    from sqlalchemy.pool import StaticPool

    from app.models import Cohorte, Perfil
    from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _activar_fk(conexion, _registro):
        conexion.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)
    with fabrica() as s:
        s.add_all(
            [
                Perfil(id=ID_ESTUDIANTE, nombre="Ana Estudiante", rol="estudiante"),
                Perfil(id=ID_DOCENTE, nombre="Diego Docente", rol="docente"),
                Perfil(id=ID_ADMIN, nombre="Alba Admin", rol="admin"),
                Cohorte(id=2, nombre="Cohorte 2", numero=2),
                Cohorte(id=1, nombre="Cohorte 1", numero=1),
            ]
        )
        s.commit()
    yield fabrica
    engine.dispose()


@pytest.fixture
def cliente_api(fabrica_api):
    """Cliente de la app real con BD de prueba y Settings inventados (sin red ni .env)."""
    from app.main import crear_app
    from tests.test_auth import ajustes, preparar

    return preparar(crear_app(ajustes()), fabrica_api, ajustes())


# Fixtures de evaluaciones (BD con laboratorio, rúbrica, entregas y evaluador falso) disponibles
# también para los tests de revisión docente, listado y traza.
from tests.test_evaluaciones import cliente, datos, evaluador  # noqa: E402, F401
