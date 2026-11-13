"""Esquemas Pydantic de las respuestas de la API (no son los del LLM)."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PerfilRespuesta(BaseModel):
    """Perfil público del usuario autenticado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    rol: Literal["estudiante", "docente", "admin"]
    foto_url: str | None
