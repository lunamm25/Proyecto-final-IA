"""Modelos de sistema: auditoría de ajustes y configuración de IA."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.tipos import JSONType, fecha_creacion, id_pk


class Auditoria(Base):
    """Registro de cambios: quién, cuándo, valor anterior, valor nuevo y motivo."""

    __tablename__ = "auditoria"
    __table_args__ = (Index("ix_auditoria_entidad", "entidad", "entidad_id"),)

    id: Mapped[int] = id_pk()
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("perfiles.id", ondelete="SET NULL"), index=True
    )
    entidad: Mapped[str] = mapped_column(Text, nullable=False)
    entidad_id: Mapped[str] = mapped_column(Text, nullable=False)
    accion: Mapped[str] = mapped_column(Text, nullable=False)
    antes: Mapped[Any | None] = mapped_column(JSONType)
    despues: Mapped[Any | None] = mapped_column(JSONType)
    motivo: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = fecha_creacion()


class ConfigIA(Base):
    """Configuración de IA activa (una sola fila con id = 1)."""

    __tablename__ = "config_ia"
    __table_args__ = (
        CheckConstraint("id = 1", name="config_ia_una_fila"),
        CheckConstraint(
            "temperatura >= 0 and temperatura <= 0.2", name="config_ia_temperatura_check"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1, autoincrement=False)
    proveedor: Mapped[str] = mapped_column(Text, nullable=False)
    modelo: Mapped[str] = mapped_column(Text, nullable=False)
    temperatura: Mapped[float] = mapped_column(Float, nullable=False)
    actualizado_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("perfiles.id", ondelete="SET NULL")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
