"""Traducción de errores de dominio y de validación a respuestas `{"detail": "..."}`."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.errores import (
    ConflictoError,
    DatosInvalidosError,
    DominioError,
    NoEncontradoError,
    ProhibidoError,
    RubricaConInconsistenciasError,
)

CODIGOS: dict[type[DominioError], int] = {
    NoEncontradoError: status.HTTP_404_NOT_FOUND,
    ProhibidoError: status.HTTP_403_FORBIDDEN,
    ConflictoError: status.HTTP_409_CONFLICT,
    DatosInvalidosError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

MENSAJES_VALIDACION = {
    "missing": "es obligatorio",
    "int_parsing": "debe ser un número entero",
    "int_type": "debe ser un número entero",
    "string_type": "debe ser texto",
    "json_invalid": "el JSON está mal formado",
    "model_attributes_type": "debe ser un objeto JSON",
    "dict_type": "debe ser un objeto JSON",
    "uuid_parsing": "debe ser un identificador UUID válido",
    "uuid_type": "debe ser un identificador UUID válido",
    "string_too_long": "es demasiado largo (máximo {max_length} caracteres)",
    "string_too_short": "no puede estar vacío",
    "greater_than_equal": "debe ser mayor o igual que {ge}",
    "less_than_equal": "debe ser menor o igual que {le}",
    "too_long": "tiene demasiados elementos (máximo {max_length})",
    "list_type": "debe ser una lista",
}


def _codigo(error: DominioError) -> int:
    """Código HTTP según la clase del error (400 si no está mapeada)."""
    for clase, codigo in CODIGOS.items():
        if isinstance(error, clase):
            return codigo
    return status.HTTP_400_BAD_REQUEST


def manejar_error_dominio(_request: Request, error: Exception) -> JSONResponse:
    """Convierte un DominioError en JSON con `detail` (y `inconsistencias` si aplica)."""
    assert isinstance(error, DominioError)
    contenido: dict[str, Any] = {"detail": error.mensaje}
    if isinstance(error, RubricaConInconsistenciasError):
        contenido["inconsistencias"] = error.inconsistencias
    return JSONResponse(status_code=_codigo(error), content=contenido)


def _describir(error: dict[str, Any]) -> str:
    """Describe un error de validación de FastAPI en español."""
    ubicacion = ".".join(str(parte) for parte in error.get("loc", ()) if parte != "body")
    plantilla = MENSAJES_VALIDACION.get(error.get("type", ""))
    if plantilla is None:
        return f"{ubicacion or 'cuerpo'}: {error.get('msg', 'no es válido')}"
    try:
        mensaje = plantilla.format(**error.get("ctx", {}))
    except (KeyError, IndexError, ValueError):
        mensaje = plantilla
    return f"{ubicacion or 'cuerpo'}: {mensaje}"


def manejar_error_validacion(_request: Request, error: Exception) -> JSONResponse:
    """Convierte los errores de validación de la petición en un único mensaje en español."""
    assert isinstance(error, RequestValidationError)
    detalles = "; ".join(dict.fromkeys(_describir(e) for e in error.errors()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": f"Datos de entrada no válidos: {detalles}."},
    )


def registrar_manejadores(aplicacion: FastAPI) -> None:
    """Registra los manejadores de errores en la aplicación."""
    aplicacion.add_exception_handler(DominioError, manejar_error_dominio)
    aplicacion.add_exception_handler(RequestValidationError, manejar_error_validacion)
