"""Rutas de evaluaciones: detalle según rol y estado (RF-05 CA6, RF-07 CA3)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import UsuarioActual
from app.api.esquemas import (
    CitaRespuesta,
    CriterioEvaluacionRespuesta,
    ErrorRespuesta,
    EvaluacionRespuesta,
    RetroalimentacionRespuesta,
)
from app.db import get_db
from app.models import EvaluacionCriterio
from app.services import evaluaciones as servicio

router = APIRouter(prefix="/api/evaluaciones", tags=["evaluaciones"])

BaseDatos = Annotated[Session, Depends(get_db)]

RESPUESTAS = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Pendiente de revisión docente"},
    404: {"model": ErrorRespuesta, "description": "Evaluación no encontrada (o ajena)"},
}


def _criterio(
    fila: EvaluacionCriterio, extra: dict[str, Any], estudiante: bool
) -> CriterioEvaluacionRespuesta:
    """Une la fila del criterio con fortalezas/debilidades guardadas en `resultado`."""
    return CriterioEvaluacionRespuesta(
        criterio_id=fila.criterio_id,
        nivel_ia=None if estudiante else fila.nivel_ia,
        nivel_final=fila.nivel_final,
        puntaje_normalizado=fila.puntaje_normalizado,
        justificacion=fila.justificacion,
        citas=[CitaRespuesta.model_validate(c) for c in fila.evidencias_verificadas or []],
        fortalezas=extra.get("fortalezas", []),
        debilidades=extra.get("debilidades", []),
        recomendacion=extra.get("recomendacion"),
        ajuste_docente=None if estudiante else fila.ajuste_docente,
    )


def _respuesta(detalle: servicio.DetalleEvaluacion) -> EvaluacionRespuesta:
    """Convierte el detalle del servicio en la respuesta (oculta trazas al estudiante)."""
    ev, estudiante = detalle.evaluacion, detalle.vista_estudiante
    resultado = ev.resultado or {}
    extras = {c.get("criterio_id"): c for c in resultado.get("criterios", [])}
    version = detalle.rubrica_version
    return EvaluacionRespuesta(
        id=ev.id,
        entrega_id=ev.entrega_id,
        estado=ev.estado,
        nota=float(ev.nota) if ev.nota is not None else None,
        rubrica_version_id=version.id if version else None,
        rubrica_version=version.version if version else None,
        proveedor=None if estudiante else ev.proveedor,
        modelo=None if estudiante else ev.modelo,
        temperatura=None if estudiante else ev.temperatura,
        prompt_version=None if estudiante else ev.prompt_version,
        error=ev.error,
        criterios=[
            _criterio(f, extras.get(f.criterio_id, {}), estudiante) for f in detalle.criterios
        ],
        retroalimentacion=RetroalimentacionRespuesta.model_validate(resultado)
        if resultado
        else None,
        creada_en=ev.creada_en,
        aprobada_en=ev.aprobada_en,
        publicada_en=ev.publicada_en,
    )


@router.get("/{evaluacion_id}", response_model=EvaluacionRespuesta, responses=RESPUESTAS)
def ver_evaluacion(
    evaluacion_id: int, perfil: UsuarioActual, db: BaseDatos
) -> EvaluacionRespuesta:
    """Detalle: docente/admin siempre; estudiante solo si es suya y está `publicada`."""
    return _respuesta(servicio.obtener_detalle(db, evaluacion_id, perfil))
