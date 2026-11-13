"""Modelos de evaluación: evaluaciones, criterios evaluados y verificación de código."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.tipos import ESTADOS_EVALUACION, IdType, JSONType, fecha_creacion, id_pk, lista_sql


class Evaluacion(Base):
    """Evaluación de una entrega con trazabilidad del modelo y estado HITL."""

    __tablename__ = "evaluaciones"
    __table_args__ = (
        CheckConstraint(
            f"estado in ({lista_sql(ESTADOS_EVALUACION)})", name="evaluaciones_estado_check"
        ),
        CheckConstraint(
            "nota is null or (nota >= 0 and nota <= 5)", name="evaluaciones_nota_check"
        ),
    )

    id: Mapped[int] = id_pk()
    entrega_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("entregas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(
        Text, nullable=False, default="borrador", server_default=text("'borrador'")
    )
    nota: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    proveedor: Mapped[str | None] = mapped_column(Text)
    modelo: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    temperatura: Mapped[float | None] = mapped_column(Float)
    respuesta_cruda: Mapped[Any | None] = mapped_column(JSONType)
    resultado: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    error: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[datetime] = fecha_creacion()
    aprobada_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("perfiles.id", ondelete="SET NULL"), index=True
    )
    aprobada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    criterios: Mapped[list["EvaluacionCriterio"]] = relationship(
        back_populates="evaluacion", cascade="all, delete-orphan"
    )
    verificacion: Mapped["VerificacionCodigo | None"] = relationship(
        back_populates="evaluacion", cascade="all, delete-orphan"
    )


class EvaluacionCriterio(Base):
    """Resultado de un criterio: nivel propuesto por la IA y nivel final del docente."""

    __tablename__ = "evaluacion_criterios"
    __table_args__ = (
        UniqueConstraint(
            "evaluacion_id", "criterio_id", name="evaluacion_criterios_evaluacion_criterio_key"
        ),
    )

    id: Mapped[int] = id_pk()
    evaluacion_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("evaluaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterio_id: Mapped[str] = mapped_column(Text, nullable=False)
    nivel_ia: Mapped[str | None] = mapped_column(Text)
    nivel_final: Mapped[str | None] = mapped_column(Text)
    puntaje_normalizado: Mapped[float | None] = mapped_column(Float)
    evidencias: Mapped[Any | None] = mapped_column(JSONType)
    evidencias_verificadas: Mapped[Any | None] = mapped_column(JSONType)
    justificacion: Mapped[str | None] = mapped_column(Text)
    ajuste_docente: Mapped[str | None] = mapped_column(Text)

    evaluacion: Mapped[Evaluacion] = relationship(back_populates="criterios")


class VerificacionCodigo(Base):
    """Resultados de la verificación técnica del código de una evaluación."""

    __tablename__ = "verificaciones_codigo"

    id: Mapped[int] = id_pk()
    evaluacion_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("evaluaciones.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    sintaxis: Mapped[Any | None] = mapped_column(JSONType)
    ruff: Mapped[Any | None] = mapped_column(JSONType)
    complejidad: Mapped[Any | None] = mapped_column(JSONType)
    tests: Mapped[Any | None] = mapped_column(JSONType)
    metricas: Mapped[Any | None] = mapped_column(JSONType)
    sandbox: Mapped[str | None] = mapped_column(Text)

    evaluacion: Mapped[Evaluacion] = relationship(back_populates="verificacion")
