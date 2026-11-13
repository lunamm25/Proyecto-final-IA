"""Modelos académicos: cohortes, laboratorios, rúbricas y temáticas."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.tipos import ESTADOS_RUBRICA, IdType, JSONType, fecha_creacion, id_pk, lista_sql


class Cohorte(Base):
    """Cohorte del curso (1 y 2)."""

    __tablename__ = "cohortes"

    id: Mapped[int] = id_pk()
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    laboratorios: Mapped[list["Laboratorio"]] = relationship(
        back_populates="cohorte", order_by="Laboratorio.codigo"
    )


class Laboratorio(Base):
    """Laboratorio de una cohorte."""

    __tablename__ = "laboratorios"

    id: Mapped[int] = id_pk()
    cohorte_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("cohortes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    codigo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    objetivos: Mapped[str | None] = mapped_column(Text)

    cohorte: Mapped[Cohorte] = relationship(back_populates="laboratorios")
    rubrica: Mapped["Rubrica | None"] = relationship(back_populates="laboratorio")


class Rubrica(Base):
    """Rúbrica de un laboratorio (una por laboratorio); el contenido vive en sus versiones."""

    __tablename__ = "rubricas"

    id: Mapped[int] = id_pk()
    laboratorio_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("laboratorios.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    laboratorio: Mapped[Laboratorio] = relationship(back_populates="rubrica")
    versiones: Mapped[list["RubricaVersion"]] = relationship(
        back_populates="rubrica", order_by="RubricaVersion.version"
    )


class RubricaVersion(Base):
    """Versión de una rúbrica; al aprobarse es inmutable."""

    __tablename__ = "rubrica_versiones"
    __table_args__ = (
        UniqueConstraint("rubrica_id", "version", name="rubrica_versiones_rubrica_version_key"),
        CheckConstraint(
            f"estado in ({lista_sql(ESTADOS_RUBRICA)})", name="rubrica_versiones_estado_check"
        ),
    )

    id: Mapped[int] = id_pk()
    rubrica_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("rubricas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    contenido: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    estado: Mapped[str] = mapped_column(
        Text, nullable=False, default="borrador", server_default=text("'borrador'")
    )
    creada_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("perfiles.id", ondelete="SET NULL"), index=True
    )
    creada_en: Mapped[datetime] = fecha_creacion()

    rubrica: Mapped[Rubrica] = relationship(back_populates="versiones")


class Tematica(Base):
    """Temática de la taxonomía del mapa mental (jerárquica vía padre_id)."""

    __tablename__ = "tematicas"

    id: Mapped[int] = id_pk()
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    padre_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("tematicas.id", ondelete="SET NULL"), index=True
    )
    descripcion: Mapped[str | None] = mapped_column(Text)
