"""Modelos de sistema: auditoría, configuración de IA y caché de resultados de IA."""

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
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.tipos import JSONType, fecha_creacion, id_pk, lista_sql


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


TIPOS_CACHE_IA = ("informe_narrativo", "mapeo_tematicas")


class CacheIA(Base):
    """Resultado de IA reutilizable (narrativa del informe o mapeo de temáticas) (0005).

    `clave`: id del estudiante (informe) o de la versión de rúbrica (mapeo). `huella`: hash de
    los datos de entrada; si cambia, se vuelve a generar. Las respuestas crudas van a auditoría.
    """

    __tablename__ = "cache_ia"
    __table_args__ = (
        UniqueConstraint("tipo", "clave", name="cache_ia_tipo_clave_key"),
        CheckConstraint(f"tipo in ({lista_sql(TIPOS_CACHE_IA)})", name="cache_ia_tipo_check"),
    )

    id: Mapped[int] = id_pk()
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    clave: Mapped[str] = mapped_column(Text, nullable=False)
    huella: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    proveedor: Mapped[str | None] = mapped_column(Text)
    modelo: Mapped[str | None] = mapped_column(Text)
    contenido: Mapped[Any] = mapped_column(JSONType, nullable=False)
    generado_en: Mapped[datetime] = fecha_creacion()
