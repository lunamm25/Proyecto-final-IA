"""Modelos SQLAlchemy del dominio (ver docs/REQUISITOS.md §10)."""

from app.models.academico import Cohorte, Laboratorio, Rubrica, RubricaVersion, Tematica
from app.models.entregas import Entrega
from app.models.evaluaciones import Evaluacion, EvaluacionCriterio, VerificacionCodigo
from app.models.sistema import Auditoria, ConfigIA
from app.models.usuarios import Perfil

__all__ = [
    "Auditoria",
    "Cohorte",
    "ConfigIA",
    "Entrega",
    "Evaluacion",
    "EvaluacionCriterio",
    "Laboratorio",
    "Perfil",
    "Rubrica",
    "RubricaVersion",
    "Tematica",
    "VerificacionCodigo",
]
