"""Dependencias de FastAPI: usuario autenticado y control de acceso por rol."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import SessionLocal, get_db
from app.models import Perfil
from app.models.tipos import ROLES
from app.services.auth import TokenInvalidoError, validar_token
from app.services.config_ia import LIMITE_PRUEBA_SEGUNDOS
from app.services.evaluador_ia import (
    Evaluador,
    ProbadorConexion,
    evaluar_con_ia,
    probar_conexion_ia,
)
from app.services.informe_ia import IAInforme, IAInformeReal
from app.services.material import CargadorMaterial, obtener_material

esquema_bearer = HTTPBearer(
    auto_error=False,
    description="JWT de Supabase (access_token de la sesión).",
)

MENSAJE_SIN_TOKEN = "No has iniciado sesión: falta el token de acceso."
MENSAJE_SIN_PERFIL = "Perfil no encontrado. Contacta al docente o administrador."
MENSAJE_SIN_PERMISO = "No tienes permisos para esta acción"


def _no_autenticado(mensaje: str) -> HTTPException:
    """Construye un 401 con el encabezado estándar `WWW-Authenticate: Bearer`."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=mensaje,
        headers={"WWW-Authenticate": "Bearer"},
    )


def usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> Perfil:
    """Valida el JWT y devuelve el perfil del usuario (el rol sale de `perfiles`)."""
    token = credenciales.credentials.strip() if credenciales else ""
    if not token:
        raise _no_autenticado(MENSAJE_SIN_TOKEN)
    try:
        usuario_id = validar_token(token, settings)
    except TokenInvalidoError as error:
        raise _no_autenticado(error.mensaje) from None
    perfil = db.get(Perfil, usuario_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MENSAJE_SIN_PERFIL)
    return perfil


def requiere_rol(*roles: str) -> Callable[..., Perfil]:
    """Crea una dependencia que exige uno de los roles; `admin` hereda lo del docente."""
    desconocidos = set(roles) - set(ROLES)
    if not roles or desconocidos:
        raise ValueError(f"Roles no válidos: {sorted(desconocidos) or 'ninguno'}")
    permitidos = set(roles) | ({"admin"} if "docente" in roles else set())

    def _verificar(perfil: Annotated[Perfil, Depends(usuario_actual)]) -> Perfil:
        if perfil.rol not in permitidos:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MENSAJE_SIN_PERMISO)
        return perfil

    return _verificar


UsuarioActual = Annotated[Perfil, Depends(usuario_actual)]
"""Atajo para declarar en una ruta: `perfil: UsuarioActual`."""


def obtener_evaluador() -> Evaluador:
    """Evaluador de IA usado por la tarea de fondo (los tests lo sustituyen)."""
    return evaluar_con_ia


def obtener_probador() -> ProbadorConexion:
    """Probador de conexión con el proveedor de IA (los tests lo sustituyen)."""
    return probar_conexion_ia


def obtener_limite_prueba_ia() -> float:
    """Tiempo máximo total, en segundos, de la prueba de conexión (los tests lo bajan)."""
    return LIMITE_PRUEBA_SEGUNDOS


def obtener_cargador_material() -> CargadorMaterial:
    """Función que obtiene el material de una entrega (provisional, ver services/material)."""
    return obtener_material


def obtener_fabrica_sesiones() -> Callable[[], Session]:
    """Fábrica de sesiones propia de la tarea de fondo (no reutiliza la de la petición)."""
    return SessionLocal


def obtener_ia_informe() -> IAInforme:
    """IA del informe y del mapa (narrativa y mapeo de temáticas); los tests la sustituyen."""
    return IAInformeReal()
