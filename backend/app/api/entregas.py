"""Rutas de entregas. Por ahora solo el lanzamiento de la evaluación con IA (RF-05)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import (
    UsuarioActual,
    obtener_cargador_material,
    obtener_evaluador,
    obtener_fabrica_sesiones,
)
from app.api.esquemas import ErrorRespuesta, EvaluacionLanzadaRespuesta
from app.config import Settings, get_settings
from app.db import get_db
from app.services import evaluaciones as servicio
from app.services.evaluador_ia import Evaluador
from app.services.material import CargadorMaterial

router = APIRouter(prefix="/api/entregas", tags=["entregas"])

BaseDatos = Annotated[Session, Depends(get_db)]

RESPUESTAS = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    404: {"model": ErrorRespuesta, "description": "Entrega no encontrada (o ajena)"},
    409: {"model": ErrorRespuesta, "description": "Evaluación en curso o rúbrica no evaluable"},
}


@router.post(
    "/{entrega_id}/evaluar",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EvaluacionLanzadaRespuesta,
    responses=RESPUESTAS,
)
def evaluar_entrega(
    entrega_id: int,
    perfil: UsuarioActual,
    db: BaseDatos,
    tareas: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    evaluador: Annotated[Evaluador, Depends(obtener_evaluador)],
    cargar_material: Annotated[CargadorMaterial, Depends(obtener_cargador_material)],
    fabrica: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones)],
) -> EvaluacionLanzadaRespuesta:
    """Lanza la evaluación con IA en segundo plano (estudiante: solo sus entregas)."""
    evaluacion = servicio.lanzar_evaluacion(db, entrega_id, perfil, settings)
    tareas.add_task(
        servicio.ejecutar_evaluacion, evaluacion.id, perfil.id, fabrica, evaluador, cargar_material
    )
    return EvaluacionLanzadaRespuesta(evaluacion_id=evaluacion.id, estado="procesando")
