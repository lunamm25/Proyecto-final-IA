"""Conexión a Postgres (Supabase) con SQLAlchemy 2, creada de forma perezosa."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos."""


class BaseDatosNoConfiguradaError(RuntimeError):
    """Se lanza cuando DATABASE_URL está vacía."""


def normalizar_database_url(url: str) -> str:
    """Convierte `postgres://` o `postgresql://` al driver psycopg (v3)."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@lru_cache
def get_engine() -> Engine:
    """Crea (una sola vez) el engine a partir de DATABASE_URL."""
    url = get_settings().database_url
    if not url.strip():
        raise BaseDatosNoConfiguradaError(
            "Falta DATABASE_URL en backend/.env. Cópiala desde el panel de Supabase."
        )
    return create_engine(normalizar_database_url(url), pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    """Fábrica de sesiones ligada al engine perezoso."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def SessionLocal() -> Session:  # noqa: N802 - nombre convencional en FastAPI
    """Abre una nueva sesión de base de datos."""
    return get_sessionmaker()()


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
