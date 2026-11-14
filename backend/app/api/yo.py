"""Ruta del perfil del usuario actual."""

from fastapi import APIRouter

from app.api.deps import UsuarioActual
from app.api.esquemas import PerfilRespuesta
from app.models import Perfil

router = APIRouter(prefix="/api", tags=["usuarios"])


@router.get(
    "/yo",
    response_model=PerfilRespuesta,
    responses={401: {"description": "No autenticado"}, 403: {"description": "Sin perfil"}},
)
def leer_yo(perfil: UsuarioActual) -> Perfil:
    """Devuelve el perfil (id, nombre, rol, foto) del usuario autenticado."""
    return perfil
