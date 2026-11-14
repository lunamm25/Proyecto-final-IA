"""Modelo de perfiles de usuario (extiende auth.users de Supabase)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.tipos import ROLES, fecha_creacion, lista_sql


class Perfil(Base):
    """Perfil con nombre, correo y rol; `id` coincide con auth.users.id."""

    __tablename__ = "perfiles"
    __table_args__ = (CheckConstraint(f"rol in ({lista_sql(ROLES)})", name="perfiles_rol_check"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    nombre: Mapped[str | None] = mapped_column(Text)
    correo: Mapped[str | None] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(
        Text, nullable=False, default="estudiante", server_default=text("'estudiante'")
    )
    foto_url: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = fecha_creacion()
