"""Rutas de configuración de IA (RF-10): solo admin. Nunca exponen claves ni URL."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import obtener_limite_prueba_ia, obtener_probador, requiere_rol
from app.api.esquemas import (
    ConfigIAEntrada,
    ConfigIARespuesta,
    ErrorRespuesta,
    PruebaConexionRespuesta,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Perfil
from app.services import config_ia as servicio
from app.services.config_ia import EstadoConfigIA, ResultadoPrueba
from app.services.evaluador_ia import ProbadorConexion

router = APIRouter(prefix="/api", tags=["config-ia"])

BaseDatos = Annotated[Session, Depends(get_db)]
Admin = Annotated[Perfil, Depends(requiere_rol("admin"))]
Ajustes = Annotated[Settings, Depends(get_settings)]
Probador = Annotated[ProbadorConexion, Depends(obtener_probador)]
LimitePrueba = Annotated[float, Depends(obtener_limite_prueba_ia)]

ERRORES_AUTH = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Solo el administrador"},
}
ERRORES_CAMBIO = {
    422: {
        "model": ErrorRespuesta,
        "description": "Proveedor o modelo no permitido, temperatura fuera de 0–0,2 o campo extra",
    },
}


@router.get("/config-ia", response_model=ConfigIARespuesta, responses=ERRORES_AUTH)
def obtener_config_ia(_admin: Admin, db: BaseDatos, settings: Ajustes) -> EstadoConfigIA:
    """Configuración vigente, claves configuradas (sí/no), opciones y versiones de prompt."""
    return servicio.obtener_config(db, settings)


@router.put(
    "/config-ia",
    response_model=ConfigIARespuesta,
    responses=ERRORES_AUTH | ERRORES_CAMBIO,
)
def cambiar_config_ia(
    entrada: ConfigIAEntrada, admin: Admin, db: BaseDatos, settings: Ajustes
) -> EstadoConfigIA:
    """Cambia proveedor, modelo y temperatura y lo deja en auditoría (igual → sin cambios)."""
    return servicio.cambiar_config(
        db, admin, entrada.proveedor, entrada.modelo, entrada.temperatura, settings
    )


@router.post("/config-ia/probar", response_model=PruebaConexionRespuesta, responses=ERRORES_AUTH)
def probar_config_ia(
    admin: Admin, db: BaseDatos, settings: Ajustes, probador: Probador, limite: LimitePrueba
) -> ResultadoPrueba:
    """Prueba la configuración guardada (máx. 10 s); siempre 200 con `ok` y mensaje genérico."""
    return servicio.probar_conexion(db, admin, settings, probador, limite)
