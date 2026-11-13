"""Esquemas Pydantic que forman el contrato con el LLM (REQUISITOS §7).

Ningún esquema incluye un campo "nota": la nota la calcula el backend de forma determinista.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class NivelDesempeno(BaseModel):
    """Nivel de desempeño de un criterio de la rúbrica."""

    nombre: str = Field(min_length=1)
    puntaje: float
    descriptor: str


class Criterio(BaseModel):
    """Criterio de evaluación con su ponderación y niveles."""

    id: str = Field(min_length=1)
    competencia: str
    nombre: str
    ponderacion: float = Field(ge=0, le=100)
    niveles: list[NivelDesempeno]

    @model_validator(mode="after")
    def _validar_niveles(self) -> "Criterio":
        """Exige al menos 2 niveles con puntajes y nombres distintos."""
        if len(self.niveles) < 2:
            raise ValueError(f"El criterio '{self.id}' debe tener al menos 2 niveles.")
        puntajes = [n.puntaje for n in self.niveles]
        if len(set(puntajes)) != len(puntajes):
            raise ValueError(f"El criterio '{self.id}' tiene niveles con puntajes repetidos.")
        nombres = [n.nombre.strip().lower() for n in self.niveles]
        if len(set(nombres)) != len(nombres):
            raise ValueError(f"El criterio '{self.id}' tiene niveles con nombres repetidos.")
        return self


class RubricaSchema(BaseModel):
    """Rúbrica completa de un laboratorio.

    La suma de ponderaciones != 100 no se rechaza aquí: es una inconsistencia que se
    reporta al docente (RF-03 CA2).
    """

    titulo: str
    criterios: list[Criterio]


class Evidencia(BaseModel):
    """Cita textual corta del material que respalda una valoración."""

    fragmento: str
    fuente: Literal["informe", "codigo", "verificacion", "imagen"]
    ubicacion: str | None = None

    @field_validator("fragmento")
    @classmethod
    def _fragmento_no_vacio(cls, valor: str) -> str:
        """Rechaza fragmentos vacíos o solo con espacios."""
        if not valor.strip():
            raise ValueError("El fragmento de la evidencia no puede estar vacío.")
        return valor


class EvaluacionCriterio(BaseModel):
    """Valoración cualitativa del LLM para un criterio."""

    criterio_id: str
    nivel_elegido: str
    evidencias: list[Evidencia] = Field(min_length=1)
    justificacion: str
    fortalezas: list[str]
    debilidades: list[str]
    recomendacion: str


class EvaluacionLLMSchema(BaseModel):
    """Respuesta completa del LLM al evaluar una entrega (sin nota)."""

    criterios: list[EvaluacionCriterio]
    aprendizajes_identificados: list[str]
    como_aplico_conocimientos: str
    aspectos_a_fortalecer: list[str]
    retroalimentacion_general: str


class AccionPlan(BaseModel):
    """Acción del plan de fortalecimiento del informe integral."""

    accion: str
    recurso: str
    prioridad: Literal["alta", "media", "baja"]
    competencia: str


class InformeNarrativoSchema(BaseModel):
    """Narrativa del informe integral del estudiante."""

    competencias_desarrolladas: list[str]
    brechas: list[str]
    plan_fortalecimiento: list[AccionPlan]
    conclusion: str


class MapeoCriterio(BaseModel):
    """Temáticas y conceptos asociados a un criterio."""

    criterio_id: str
    tematicas: list[str]
    conceptos: list[str]


class MapeoTematicasSchema(BaseModel):
    """Mapeo de criterios a temáticas para el mapa mental."""

    mapeos: list[MapeoCriterio]
