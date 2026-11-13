"""Tipos y columnas comunes compartidos por los modelos."""

from sqlalchemy import JSON, BigInteger, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

# jsonb en Postgres; JSON genérico en SQLite (tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")

# bigint en Postgres; INTEGER en SQLite para que funcione el autoincremento.
IdType = BigInteger().with_variant(Integer(), "sqlite")

ESTADOS_EVALUACION = ("borrador", "en_revision", "aprobada", "publicada", "error")
ESTADOS_RUBRICA = ("borrador", "aprobada")
ROLES = ("estudiante", "docente", "admin")


def lista_sql(valores: tuple[str, ...]) -> str:
    """Convierte una tupla de textos en la lista SQL usada en los CHECK."""
    return ", ".join(f"'{v}'" for v in valores)


def id_pk():
    """Columna de clave primaria autoincremental."""
    return mapped_column(IdType, primary_key=True, autoincrement=True)


def fecha_creacion():
    """Columna de fecha de creación con valor por defecto en el servidor."""
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
