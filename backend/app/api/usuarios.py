"""Rutas de gestión de usuarios y roles (RF-01 CA3): solo admin."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import requiere_rol
from app.api.esquemas import CambioRolEntrada, ErrorRespuesta, UsuarioRespuesta
from app.db import get_db
from app.models import Perfil
from app.services import usuarios as servicio

router = APIRouter(prefix="/api", tags=["usuarios"])

BaseDatos = Annotated[Session, Depends(get_db)]
Admin = Annotated[Perfil, Depends(requiere_rol("admin"))]

ERRORES_AUTH = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Solo el administrador"},
}
ERRORES_CAMBIO = {
    404: {"model": ErrorRespuesta, "description": "El usuario no existe"},
    409: {"model": ErrorRespuesta, "description": "Dejaría el sistema sin administrador"},
    422: {"model": ErrorRespuesta, "description": "Rol o datos no válidos"},
}


@router.get("/usuarios", response_model=list[UsuarioRespuesta], responses=ERRORES_AUTH)
def listar_usuarios(_admin: Admin, db: BaseDatos) -> list[Perfil]:
    """Lista los usuarios con id, nombre, correo y rol, ordenados por nombre (solo admin)."""
    return servicio.listar_usuarios(db)


@router.patch(
    "/usuarios/{usuario_id}/rol",
    response_model=UsuarioRespuesta,
    responses=ERRORES_AUTH | ERRORES_CAMBIO,
)
def cambiar_rol(
    usuario_id: uuid.UUID, entrada: CambioRolEntrada, admin: Admin, db: BaseDatos
) -> Perfil:
    """Cambia el rol de un usuario y lo deja en auditoría (solo admin)."""
    return servicio.cambiar_rol(db, admin, usuario_id, entrada.rol, entrada.motivo)
