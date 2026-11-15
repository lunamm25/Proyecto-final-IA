"""Utilidades de fechas compartidas por servicios y rutas."""

from datetime import UTC, datetime


def a_utc(fecha: datetime | None) -> datetime | None:
    """Fecha con zona UTC (SQLite devuelve fechas sin zona: se tratan como UTC)."""
    if fecha is None:
        return None
    return fecha.replace(tzinfo=UTC) if fecha.tzinfo is None else fecha.astimezone(UTC)
