"""Esquemas Pydantic de las respuestas de la API (no son los del LLM)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PerfilRespuesta(BaseModel):
    """Perfil público del usuario autenticado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    rol: Literal["estudiante", "docente", "admin"]
    foto_url: str | None


class UsuarioRespuesta(BaseModel):
    """Usuario en la gestión de roles (solo admin)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    correo: str | None
    rol: Literal["estudiante", "docente", "admin"]


class CambioRolEntrada(BaseModel):
    """Nuevo rol de un usuario y motivo opcional (queda en auditoría)."""

    rol: str = Field(
        description="Uno de: estudiante, docente o admin.",
        json_schema_extra={"enum": ["estudiante", "docente", "admin"]},
        examples=["docente"],
    )
    motivo: str | None = Field(default=None, max_length=500, examples=["Monitor del curso"])


class LaboratorioEntrada(BaseModel):
    """Datos para crear o editar un laboratorio."""

    cohorte_id: int
    codigo: str
    titulo: str
    descripcion: str | None = None
    objetivos: str | None = None


class LaboratorioRespuesta(BaseModel):
    """Laboratorio de una cohorte."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cohorte_id: int
    codigo: str
    titulo: str
    descripcion: str | None
    objetivos: str | None


class LaboratorioEnCohorte(LaboratorioRespuesta):
    """Laboratorio con el número de su versión de rúbrica vigente (None si no tiene)."""

    version_rubrica_vigente: int | None = None


class CohorteRespuesta(BaseModel):
    """Cohorte con sus laboratorios ordenados por código."""

    id: int
    nombre: str
    numero: int
    laboratorios: list[LaboratorioEnCohorte]


class ValidacionRubricaRespuesta(BaseModel):
    """Resultado del validador: válida si no hay inconsistencias."""

    valida: bool
    inconsistencias: list[str]


class RubricaVersionRespuesta(BaseModel):
    """Versión inmutable de una rúbrica."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    estado: Literal["borrador", "aprobada"]
    contenido: dict[str, Any]
    creada_por: uuid.UUID | None
    creada_en: datetime


class ErrorRespuesta(BaseModel):
    """Forma estándar de los errores: mensaje en español."""

    detail: str


class ErrorRubricaRespuesta(ErrorRespuesta):
    """Error 422 al guardar una rúbrica con inconsistencias."""

    inconsistencias: list[str]


EstadoEvaluacion = Literal[
    "procesando", "borrador", "en_revision", "aprobada", "publicada", "error"
]


class EvaluacionLanzadaRespuesta(BaseModel):
    """Respuesta 202 al lanzar una evaluación: se procesa en segundo plano."""

    evaluacion_id: int
    estado: EstadoEvaluacion = Field(examples=["procesando"])


class CitaRespuesta(BaseModel):
    """Evidencia citada por la IA y su verificación contra el material (similitud 0–100)."""

    fragmento: str
    fuente: str
    ubicacion: str | None = None
    verificada: bool
    similitud: float


class CriterioEvaluacionRespuesta(BaseModel):
    """Resultado de un criterio. `nivel_ia` y `ajuste_docente` solo los ve el docente."""

    criterio_id: str
    nivel_ia: str | None = None
    nivel_final: str | None
    puntaje_normalizado: float | None
    justificacion: str | None
    citas: list[CitaRespuesta]
    fortalezas: list[str] = []
    debilidades: list[str] = []
    recomendacion: str | None = None
    ajuste_docente: str | None = None


class RetroalimentacionRespuesta(BaseModel):
    """Retroalimentación general de la evaluación."""

    aprendizajes_identificados: list[str] = []
    como_aplico_conocimientos: str | None = None
    aspectos_a_fortalecer: list[str] = []
    retroalimentacion_general: str | None = None


class EvaluacionRespuesta(BaseModel):
    """Detalle de una evaluación (nunca incluye respuestas crudas del LLM).

    Para el estudiante, proveedor, modelo, temperatura y prompt_version van en null.
    """

    id: int
    entrega_id: int
    estado: EstadoEvaluacion
    nota: float | None
    rubrica_version_id: int | None
    rubrica_version: int | None
    proveedor: str | None = None
    modelo: str | None = None
    temperatura: float | None = None
    prompt_version: str | None = None
    error: str | None
    criterios: list[CriterioEvaluacionRespuesta]
    retroalimentacion: RetroalimentacionRespuesta | None
    creada_en: datetime
    aprobada_en: datetime | None
    publicada_en: datetime | None
