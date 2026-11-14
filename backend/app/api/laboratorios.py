"""Rutas de cohortes y laboratorios (RF-02)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioActual, requiere_rol
from app.api.esquemas import (
    CohorteRespuesta,
    ErrorRespuesta,
    LaboratorioEnCohorte,
    LaboratorioEntrada,
    LaboratorioRespuesta,
)
from app.db import get_db
from app.models import Laboratorio, Perfil
from app.services import laboratorios as servicio

router = APIRouter(prefix="/api", tags=["cohortes y laboratorios"])

BaseDatos = Annotated[Session, Depends(get_db)]
Docente = Annotated[Perfil, Depends(requiere_rol("docente"))]

ERRORES_AUTH = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Sin permisos"},
}
ERROR_404 = {404: {"model": ErrorRespuesta, "description": "Laboratorio no encontrado"}}
ERROR_409 = {409: {"model": ErrorRespuesta, "description": "Conflicto"}}
ERROR_422 = {422: {"model": ErrorRespuesta, "description": "Datos no válidos"}}


def _datos(entrada: LaboratorioEntrada) -> servicio.DatosLaboratorio:
    """Convierte el cuerpo de la petición en los datos del servicio."""
    return servicio.DatosLaboratorio(**entrada.model_dump())


@router.get("/cohortes", response_model=list[CohorteRespuesta], responses=ERRORES_AUTH)
def listar_cohortes(_perfil: UsuarioActual, db: BaseDatos) -> list[CohorteRespuesta]:
    """Cohortes ordenadas por número con sus laboratorios y versión de rúbrica vigente."""
    vigentes = servicio.versiones_vigentes(db)
    return [
        CohorteRespuesta(
            id=c.id,
            nombre=c.nombre,
            numero=c.numero,
            laboratorios=[
                LaboratorioEnCohorte.model_validate(lab).model_copy(
                    update={"version_rubrica_vigente": vigentes.get(lab.id)}
                )
                for lab in c.laboratorios
            ],
        )
        for c in servicio.listar_cohortes(db)
    ]


@router.post(
    "/laboratorios",
    status_code=status.HTTP_201_CREATED,
    response_model=LaboratorioRespuesta,
    responses=ERRORES_AUTH | ERROR_409 | ERROR_422,
)
def crear_laboratorio(entrada: LaboratorioEntrada, _perfil: Docente, db: BaseDatos) -> Laboratorio:
    """Crea un laboratorio en una cohorte (solo docente)."""
    return servicio.crear_laboratorio(db, _datos(entrada))


@router.put(
    "/laboratorios/{laboratorio_id}",
    response_model=LaboratorioRespuesta,
    responses=ERRORES_AUTH | ERROR_404 | ERROR_409 | ERROR_422,
)
def editar_laboratorio(
    laboratorio_id: int, entrada: LaboratorioEntrada, _perfil: Docente, db: BaseDatos
) -> Laboratorio:
    """Edita un laboratorio (solo docente)."""
    return servicio.actualizar_laboratorio(db, laboratorio_id, _datos(entrada))


@router.delete(
    "/laboratorios/{laboratorio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=ERRORES_AUTH | ERROR_404 | ERROR_409,
)
def borrar_laboratorio(laboratorio_id: int, _perfil: Docente, db: BaseDatos) -> Response:
    """Borra un laboratorio sin entregas, con su rúbrica y versiones (solo docente)."""
    servicio.borrar_laboratorio(db, laboratorio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
