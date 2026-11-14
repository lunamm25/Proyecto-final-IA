"""Esquemas Pydantic de las respuestas de la API (no son los del LLM)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PerfilRespuesta(BaseModel):
    """Perfil público del usuario autenticado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    rol: Literal["estudiante", "docente", "admin"]
    foto_url: str | None


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
