"""Rutas de entregas: crear (RF-04), portafolio paginado y lanzamiento de la evaluación (RF-05)."""

import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import (
    UsuarioActual,
    obtener_almacen,
    obtener_cargador_material,
    obtener_evaluador,
    obtener_fabrica_sesiones,
    requiere_rol,
)
from app.api.esquemas import (
    EntregaRespuesta,
    ErrorRespuesta,
    EstudianteResumen,
    EvaluacionLanzadaRespuesta,
    LaboratorioResumen,
    ListadoEntregasRespuesta,
    UltimaEvaluacionResumen,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Evaluacion, Perfil
from app.services import entregas as servicio_entregas
from app.services import evaluaciones as servicio
from app.services.almacen import AlmacenArchivos
from app.services.entregas import ArchivoEntrada, FilaEntrega
from app.services.evaluador_ia import Evaluador
from app.services.fechas import a_utc
from app.services.material import CargadorMaterial

router = APIRouter(prefix="/api/entregas", tags=["entregas"])

BaseDatos = Annotated[Session, Depends(get_db)]
Estudiante = Annotated[Perfil, Depends(requiere_rol("estudiante"))]

LIMIT_POR_DEFECTO = 20
LIMIT_MAXIMO = 100
ESTADOS_VISIBLES_ESTUDIANTE = ("procesando", "error", "publicada")

RESPUESTAS = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    404: {"model": ErrorRespuesta, "description": "Entrega no encontrada (o ajena)"},
    409: {"model": ErrorRespuesta, "description": "Evaluación en curso o rúbrica no evaluable"},
}
RESPUESTAS_CREAR = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Solo estudiantes"},
    413: {"model": ErrorRespuesta, "description": "Archivo demasiado grande (máx. 20 MB)"},
    422: {"model": ErrorRespuesta, "description": "Datos o archivos no válidos"},
    503: {"model": ErrorRespuesta, "description": "No se pudo guardar en el almacén"},
}
RESPUESTAS_LISTAR = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    404: {"model": ErrorRespuesta, "description": "Estudiante no encontrado (o ajeno)"},
    422: {"model": ErrorRespuesta, "description": "Parámetros no válidos"},
}


def _numero(valor: Decimal | None) -> float | None:
    """Nota numeric → float para JSON."""
    return float(valor) if valor is not None else None


def _ultima(
    evaluacion: Evaluacion | None, vista_estudiante: bool
) -> UltimaEvaluacionResumen | None:
    """Estado y nota reales para docente; el estudiante solo ve la nota si está publicada."""
    if evaluacion is None:
        return None
    if vista_estudiante and evaluacion.estado not in ESTADOS_VISIBLES_ESTUDIANTE:
        return UltimaEvaluacionResumen(id=evaluacion.id, estado="pendiente_revision", nota=None)
    nota = _numero(evaluacion.nota)
    if vista_estudiante and evaluacion.estado != "publicada":
        nota = None
    return UltimaEvaluacionResumen(id=evaluacion.id, estado=evaluacion.estado, nota=nota)


def _item(fila: FilaEntrega, vista_estudiante: bool) -> EntregaRespuesta:
    """Entrega para la respuesta (sin rutas del bucket)."""
    entrega = fila.entrega
    return EntregaRespuesta(
        id=entrega.id,
        laboratorio=LaboratorioResumen.model_validate(fila.laboratorio, from_attributes=True),
        estudiante=EstudianteResumen(id=fila.estudiante.id, nombre=fila.estudiante.nombre),
        rubrica_version_id=entrega.rubrica_version_id,
        rubrica_version=fila.rubrica_version.version if fila.rubrica_version else None,
        tiene_pdf=bool(entrega.pdf_path),
        tiene_zip=bool(entrega.codigo_zip_path),
        github_url=entrega.github_url,
        creada_en=a_utc(entrega.creada_en),
        ultima_evaluacion=_ultima(fila.ultima_evaluacion, vista_estudiante),
    )


def _archivo(subido: UploadFile | None) -> ArchivoEntrada | None:
    """Archivo recibido o None si no se adjuntó (o llegó vacío). El nombre se ignora."""
    if subido is None or subido.size == 0:
        return None
    return ArchivoEntrada(flujo=subido.file, content_type=subido.content_type)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EntregaRespuesta,
    responses=RESPUESTAS_CREAR,
)
def crear_entrega(
    estudiante: Estudiante,
    db: BaseDatos,
    settings: Annotated[Settings, Depends(get_settings)],
    almacen: Annotated[AlmacenArchivos, Depends(obtener_almacen)],
    laboratorio_id: Annotated[int, Form()],
    pdf: Annotated[
        UploadFile | None, File(description="Informe en PDF con texto (obligatorio).")
    ] = None,
    codigo_zip: Annotated[
        UploadFile | None, File(alias="zip", description="Código en ZIP, opcional (≤ 20 MB).")
    ] = None,
    github_url: Annotated[
        str | None, Form(description="Opcional: https://github.com/usuario/repo")
    ] = None,
    extras: Annotated[str | None, Form(description="Objeto JSON pequeño (opcional).")] = None,
) -> EntregaRespuesta:
    """Crea la entrega del estudiante: PDF obligatorio; ZIP y URL de GitHub opcionales."""
    fila = servicio_entregas.crear_entrega(
        db,
        estudiante,
        laboratorio_id=laboratorio_id,
        pdf=_archivo(pdf),
        codigo_zip=_archivo(codigo_zip),
        github_url=github_url,
        extras=extras,
        almacen=almacen,
        settings=settings,
    )
    return _item(fila, vista_estudiante=True)


@router.get("", response_model=ListadoEntregasRespuesta, responses=RESPUESTAS_LISTAR)
def listar_entregas(
    perfil: UsuarioActual,
    db: BaseDatos,
    estudiante_id: uuid.UUID | None = None,
    laboratorio_id: int | None = None,
    limit: int = Query(default=LIMIT_POR_DEFECTO, ge=1, le=LIMIT_MAXIMO),
    offset: int = Query(default=0, ge=0),
) -> ListadoEntregasRespuesta:
    """Portafolio: el estudiante ve las suyas; docente/admin, las de cualquiera."""
    pagina = servicio_entregas.listar_entregas(
        db,
        perfil,
        estudiante_id=estudiante_id,
        laboratorio_id=laboratorio_id,
        limit=limit,
        offset=offset,
    )
    vista_estudiante = perfil.rol not in ("docente", "admin")
    return ListadoEntregasRespuesta(
        items=[_item(f, vista_estudiante) for f in pagina.filas],
        total=pagina.total,
        limit=limit,
        offset=offset,
    )


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
        servicio.ejecutar_evaluacion,
        evaluacion.id,
        perfil.id,
        fabrica,
        evaluador,
        cargar_material,
        settings,
    )
    return EvaluacionLanzadaRespuesta(evaluacion_id=evaluacion.id, estado="procesando")
