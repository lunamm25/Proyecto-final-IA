"""Rutas de evaluaciones: detalle por rol (RF-05 CA6) y revisión docente HITL (RF-07)."""

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import UsuarioActual, requiere_rol
from app.api.esquemas import (
    AjusteCriterioEntrada,
    CitaRespuesta,
    CriterioEvaluacionRespuesta,
    ErrorRespuesta,
    EstudianteResumen,
    EvaluacionRespuesta,
    EvaluacionResumen,
    EventoTrazaRespuesta,
    LaboratorioResumen,
    ListadoEvaluacionesRespuesta,
    RetroalimentacionCriterioIA,
    RetroalimentacionEntrada,
    RetroalimentacionRespuesta,
    TrazaRespuesta,
    UsuarioTraza,
)
from app.db import get_db
from app.models import EvaluacionCriterio, Perfil
from app.services import evaluaciones as servicio
from app.services import revision, traza
from app.services.traza import a_utc, sin_secretos

router = APIRouter(prefix="/api/evaluaciones", tags=["evaluaciones"])

BaseDatos = Annotated[Session, Depends(get_db)]
Docente = Annotated[Perfil, Depends(requiere_rol("docente"))]

LIMIT_POR_DEFECTO = 20
LIMIT_MAXIMO = 100

RESPUESTAS = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Pendiente de revisión docente"},
    404: {"model": ErrorRespuesta, "description": "Evaluación no encontrada (o ajena)"},
}
RESPUESTAS_DOCENTE = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Solo docente o administrador"},
    404: {"model": ErrorRespuesta, "description": "Evaluación (o criterio) no encontrada"},
}
RESPUESTAS_ACCION = RESPUESTAS_DOCENTE | {
    409: {"model": ErrorRespuesta, "description": "No permitido en el estado actual"},
    422: {"model": ErrorRespuesta, "description": "Datos no válidos"},
}


def _numero(valor: Decimal | None) -> float | None:
    """Nota numeric → float para JSON."""
    return float(valor) if valor is not None else None


def _criterio(
    fila: EvaluacionCriterio, detalle: servicio.DetalleEvaluacion
) -> CriterioEvaluacionRespuesta:
    """Criterio con el texto final (editado o de la IA); el original solo para el docente."""
    estudiante = detalle.vista_estudiante
    final = revision.retro_criterio_final(fila, detalle.evaluacion)
    original = revision.retro_criterio_ia(fila, detalle.evaluacion)
    return CriterioEvaluacionRespuesta(
        criterio_id=fila.criterio_id,
        nivel_ia=None if estudiante else fila.nivel_ia,
        nivel_final=fila.nivel_final,
        puntaje_normalizado=fila.puntaje_normalizado,
        citas=[CitaRespuesta.model_validate(c) for c in fila.evidencias_verificadas or []],
        ajuste_docente=None if estudiante else fila.ajuste_docente,
        original_ia=None if estudiante else RetroalimentacionCriterioIA.model_validate(original),
        **final,
    )


def _respuesta(detalle: servicio.DetalleEvaluacion) -> EvaluacionRespuesta:
    """Convierte el detalle del servicio en la respuesta (oculta trazas al estudiante)."""
    ev, estudiante = detalle.evaluacion, detalle.vista_estudiante
    version = detalle.rubrica_version
    final = revision.retro_general_final(ev)
    original = revision.retro_general_ia(ev)
    return EvaluacionRespuesta(
        id=ev.id,
        entrega_id=ev.entrega_id,
        estado=ev.estado,
        nota=_numero(ev.nota),
        rubrica_version_id=version.id if version else None,
        rubrica_version=version.version if version else None,
        proveedor=None if estudiante else ev.proveedor,
        modelo=None if estudiante else ev.modelo,
        temperatura=None if estudiante else ev.temperatura,
        prompt_version=None if estudiante else ev.prompt_version,
        error=ev.error,
        criterios=[_criterio(f, detalle) for f in detalle.criterios],
        retroalimentacion=RetroalimentacionRespuesta.model_validate(final) if final else None,
        retroalimentacion_ia=None
        if estudiante or not original
        else RetroalimentacionRespuesta.model_validate(original),
        creada_en=a_utc(ev.creada_en),
        aprobada_en=a_utc(ev.aprobada_en),
        publicada_en=a_utc(ev.publicada_en),
    )


def _detalle(db: Session, evaluacion_id: int, perfil: Perfil) -> EvaluacionRespuesta:
    """Detalle actualizado tras una acción."""
    return _respuesta(servicio.obtener_detalle(db, evaluacion_id, perfil))


def _item(fila: servicio.FilaListado) -> EvaluacionResumen:
    """Fila del listado docente."""
    ev = fila.evaluacion
    return EvaluacionResumen(
        id=ev.id,
        entrega_id=ev.entrega_id,
        estudiante=EstudianteResumen(id=fila.estudiante.id, nombre=fila.estudiante.nombre),
        laboratorio=LaboratorioResumen.model_validate(fila.laboratorio, from_attributes=True),
        estado=ev.estado,
        nota=_numero(ev.nota),
        creada_en=a_utc(ev.creada_en),
        aprobada_en=a_utc(ev.aprobada_en),
        publicada_en=a_utc(ev.publicada_en),
    )


@router.get("", response_model=ListadoEvaluacionesRespuesta, responses=RESPUESTAS_ACCION)
def listar_evaluaciones(
    _docente: Docente,
    db: BaseDatos,
    laboratorio_id: int | None = None,
    estado: str | None = Query(default=None, description="Uno de los estados de evaluación."),
    estudiante_id: uuid.UUID | None = None,
    limit: int = Query(default=LIMIT_POR_DEFECTO, ge=1, le=LIMIT_MAXIMO),
    offset: int = Query(default=0, ge=0),
) -> ListadoEvaluacionesRespuesta:
    """Listado docente con filtros, de la más reciente a la más antigua (paginado)."""
    pagina = servicio.listar_evaluaciones(
        db,
        laboratorio_id=laboratorio_id,
        estado=estado,
        estudiante_id=estudiante_id,
        limit=limit,
        offset=offset,
    )
    return ListadoEvaluacionesRespuesta(
        items=[_item(f) for f in pagina.filas], total=pagina.total, limit=limit, offset=offset
    )


@router.get("/{evaluacion_id}", response_model=EvaluacionRespuesta, responses=RESPUESTAS)
def ver_evaluacion(evaluacion_id: int, perfil: UsuarioActual, db: BaseDatos) -> EvaluacionRespuesta:
    """Detalle: docente/admin siempre; estudiante solo si es suya y está `publicada`."""
    return _detalle(db, evaluacion_id, perfil)


@router.post(
    "/{evaluacion_id}/revisar", response_model=EvaluacionRespuesta, responses=RESPUESTAS_ACCION
)
def pasar_a_revision(evaluacion_id: int, docente: Docente, db: BaseDatos) -> EvaluacionRespuesta:
    """borrador → en_revision."""
    revision.pasar_a_revision(db, evaluacion_id, docente)
    return _detalle(db, evaluacion_id, docente)


@router.patch(
    "/{evaluacion_id}/criterios/{criterio_id}",
    response_model=EvaluacionRespuesta,
    responses=RESPUESTAS_ACCION,
)
def ajustar_criterio(
    evaluacion_id: int,
    criterio_id: str,
    entrada: AjusteCriterioEntrada,
    docente: Docente,
    db: BaseDatos,
) -> EvaluacionRespuesta:
    """Cambia el nivel final de un criterio (motivo obligatorio); el backend recalcula la nota."""
    revision.ajustar_criterio(
        db, evaluacion_id, criterio_id, entrada.nivel_final, entrada.motivo, docente
    )
    return _detalle(db, evaluacion_id, docente)


@router.patch(
    "/{evaluacion_id}/retroalimentacion",
    response_model=EvaluacionRespuesta,
    responses=RESPUESTAS_ACCION,
)
def editar_retroalimentacion(
    evaluacion_id: int, entrada: RetroalimentacionEntrada, docente: Docente, db: BaseDatos
) -> EvaluacionRespuesta:
    """Edita la retroalimentación general y/o de criterios; el texto de la IA se conserva."""
    general = entrada.model_dump(include=set(revision.CAMPOS_GENERALES), exclude_unset=True)
    criterios = [c.model_dump(exclude_unset=True) for c in entrada.criterios]
    revision.editar_retroalimentacion(
        db, evaluacion_id, general, criterios, entrada.motivo, docente
    )
    return _detalle(db, evaluacion_id, docente)


@router.post(
    "/{evaluacion_id}/aprobar", response_model=EvaluacionRespuesta, responses=RESPUESTAS_ACCION
)
def aprobar(evaluacion_id: int, docente: Docente, db: BaseDatos) -> EvaluacionRespuesta:
    """en_revision → aprobada (confirma la nota y guarda quién y cuándo)."""
    revision.aprobar(db, evaluacion_id, docente)
    return _detalle(db, evaluacion_id, docente)


@router.post(
    "/{evaluacion_id}/publicar", response_model=EvaluacionRespuesta, responses=RESPUESTAS_ACCION
)
def publicar(evaluacion_id: int, docente: Docente, db: BaseDatos) -> EvaluacionRespuesta:
    """aprobada → publicada: desde ahora la ve el estudiante."""
    revision.publicar(db, evaluacion_id, docente)
    return _detalle(db, evaluacion_id, docente)


@router.get("/{evaluacion_id}/traza", response_model=TrazaRespuesta, responses=RESPUESTAS_DOCENTE)
def ver_traza(evaluacion_id: int, _docente: Docente, db: BaseDatos) -> TrazaRespuesta:
    """Trazabilidad completa (incluye respuestas crudas; nunca claves)."""
    datos = traza.obtener_traza(db, evaluacion_id)
    ev, version = datos.evaluacion, datos.rubrica_version
    return TrazaRespuesta(
        evaluacion_id=ev.id,
        entrega_id=ev.entrega_id,
        estado=ev.estado,
        nota=_numero(ev.nota),
        proveedor=ev.proveedor,
        modelo=ev.modelo,
        temperatura=ev.temperatura,
        prompt_version=ev.prompt_version,
        rubrica_version_id=version.id if version else None,
        rubrica_version=version.version if version else None,
        eventos=[
            EventoTrazaRespuesta(
                id=e.auditoria.id,
                fecha=a_utc(e.auditoria.creado_en),
                usuario=None
                if e.auditoria.usuario_id is None
                else UsuarioTraza(
                    id=e.auditoria.usuario_id, nombre=e.usuario.nombre if e.usuario else None
                ),
                accion=e.auditoria.accion,
                antes=sin_secretos(e.auditoria.antes),
                despues=sin_secretos(e.auditoria.despues),
                motivo=e.auditoria.motivo,
            )
            for e in datos.eventos
        ],
    )
