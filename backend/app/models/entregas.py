"""Modelo de entregas del portafolio académico."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.tipos import IdType, JSONType, fecha_creacion, id_pk


class Entrega(Base):
    """Entrega de un estudiante para un laboratorio, ligada a la versión de rúbrica vigente."""

    __tablename__ = "entregas"

    id: Mapped[int] = id_pk()
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("perfiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    laboratorio_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("laboratorios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rubrica_version_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("rubrica_versiones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pdf_path: Mapped[str] = mapped_column(Text, nullable=False)
    codigo_zip_path: Mapped[str | None] = mapped_column(Text)
    github_url: Mapped[str | None] = mapped_column(Text)
    extras: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    creada_en: Mapped[datetime] = fecha_creacion()
