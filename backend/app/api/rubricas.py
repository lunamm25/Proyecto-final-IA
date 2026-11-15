"""Rutas de rúbricas: validación, versiones y versión vigente (RF-03)."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioActual, obtener_extractor_rubrica, requiere_rol
from app.api.esquemas import (
    ErrorRespuesta,
    ErrorRubricaRespuesta,
    ExtraccionRubricaRespuesta,
    RubricaVersionRespuesta,
    ValidacionRubricaRespuesta,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Perfil, RubricaVersion
from app.services import rubricas as servicio
from app.services import rubricas_ia
from app.services.archivos import ArchivoEntrada
from app.services.extractor_rubrica import ExtractorRubrica

router = APIRouter(prefix="/api", tags=["rúbricas"])

BaseDatos = Annotated[Session, Depends(get_db)]
Docente = Annotated[Perfil, Depends(requiere_rol("docente"))]

EJEMPLO_RUBRICA = {
    "titulo": "Laboratorio 1",
    "criterios": [
        {
            "id": "c1",
            "competencia": "Programación",
            "nombre": "Calidad del código",
            "ponderacion": 100,
            "niveles": [
                {"nombre": "Excelente", "puntaje": 5, "descriptor": "Código claro y probado"},
                {"nombre": "Insuficiente", "puntaje": 1, "descriptor": "Código confuso"},
            ],
        }
    ],
}
CuerpoRubrica = Annotated[
    Any, Body(description="Rúbrica en formato RubricaSchema.", examples=[EJEMPLO_RUBRICA])
]

ERRORES_AUTH = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Sin permisos"},
}
ERROR_404 = {404: {"model": ErrorRespuesta, "description": "No encontrado"}}
ERRORES_EXTRAER = {
    413: {"model": ErrorRespuesta, "description": "PDF demasiado grande (máx. 20 MB)"},
    422: {"model": ErrorRespuesta, "description": "Falta el archivo, no es PDF o no tiene texto"},
    503: {"model": ErrorRespuesta, "description": "La IA no pudo extraer la rúbrica"},
}


@router.post(
    "/rubricas/validar", response_model=ValidacionRubricaRespuesta, responses=ERRORES_AUTH
)
def validar_rubrica(
    _perfil: Docente, rubrica: CuerpoRubrica = None
) -> ValidacionRubricaRespuesta:
    """Valida una rúbrica y lista sus inconsistencias (solo docente)."""
    inconsistencias = servicio.validar_rubrica(rubrica)
    return ValidacionRubricaRespuesta(valida=not inconsistencias, inconsistencias=inconsistencias)


@router.post(
    "/laboratorios/{laboratorio_id}/rubrica/versiones",
    status_code=status.HTTP_201_CREATED,
    response_model=RubricaVersionRespuesta,
    responses=ERRORES_AUTH
    | ERROR_404
    | {
        409: {"model": ErrorRespuesta, "description": "Versión guardada a la vez por otra persona"},
        422: {"model": ErrorRubricaRespuesta, "description": "Rúbrica con inconsistencias"},
    },
)
def guardar_version(
    laboratorio_id: int, perfil: Docente, db: BaseDatos, rubrica: CuerpoRubrica = None
) -> RubricaVersion:
    """Guarda y aprueba una versión nueva e inmutable de la rúbrica (solo docente)."""
    return servicio.guardar_version(db, laboratorio_id, rubrica, perfil.id)


@router.get(
    "/laboratorios/{laboratorio_id}/rubrica",
    response_model=RubricaVersionRespuesta,
    responses=ERRORES_AUTH | ERROR_404,
)
def leer_rubrica_vigente(
    laboratorio_id: int, _perfil: UsuarioActual, db: BaseDatos
) -> RubricaVersion:
    """Versión vigente (la aprobada de mayor número) de la rúbrica del laboratorio."""
    return servicio.leer_version_vigente(db, laboratorio_id)


@router.post(
    "/laboratorios/{laboratorio_id}/rubrica/extraer",
    response_model=ExtraccionRubricaRespuesta,
    responses=ERRORES_AUTH | ERROR_404 | ERRORES_EXTRAER,
)
def extraer_rubrica(
    laboratorio_id: int,
    perfil: Docente,
    db: BaseDatos,
    settings: Annotated[Settings, Depends(get_settings)],
    extractor: Annotated[ExtractorRubrica, Depends(obtener_extractor_rubrica)],
    archivo: Annotated[UploadFile, File(description="Enunciado en PDF con texto (≤ 20 MB).")],
) -> ExtraccionRubricaRespuesta:
    """Propone la rúbrica a partir del enunciado en PDF (no la guarda; solo docente)."""
    propuesta = rubricas_ia.extraer_de_pdf(
        db,
        laboratorio_id,
        ArchivoEntrada(flujo=archivo.file, content_type=archivo.content_type),
        perfil,
        settings,
        extractor,
    )
    return ExtraccionRubricaRespuesta(
        rubrica=propuesta.rubrica,
        valida=propuesta.valida,
        inconsistencias=propuesta.inconsistencias,
    )
