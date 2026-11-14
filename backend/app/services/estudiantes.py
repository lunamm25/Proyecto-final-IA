"""Listado de estudiantes para el docente (RF-08): datos básicos y laboratorios evaluados."""

from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import Entrega, Evaluacion, Perfil


@dataclass(frozen=True)
class FilaEstudiante:
    """Estudiante y número de laboratorios distintos con al menos una evaluación publicada."""

    perfil: Perfil
    laboratorios_evaluados: int


@dataclass(frozen=True)
class PaginaEstudiantes:
    """Una página del listado y el total de estudiantes."""

    filas: list[FilaEstudiante]
    total: int


def listar_estudiantes(db: Session, *, limit: int, offset: int) -> PaginaEstudiantes:
    """Estudiantes por nombre (sin distinguir mayúsculas; sin nombre al final), paginados."""
    evaluados = (
        select(
            Entrega.estudiante_id.label("estudiante_id"),
            func.count(distinct(Entrega.laboratorio_id)).label("laboratorios"),
        )
        .join(Evaluacion, Evaluacion.entrega_id == Entrega.id)
        .where(Evaluacion.estado == "publicada")
        .group_by(Entrega.estudiante_id)
        .subquery()
    )
    consulta = (
        select(Perfil, func.coalesce(evaluados.c.laboratorios, 0))
        .outerjoin(evaluados, evaluados.c.estudiante_id == Perfil.id)
        .where(Perfil.rol == "estudiante")
        .order_by(Perfil.nombre.is_(None), func.lower(Perfil.nombre), Perfil.id)
        .limit(limit)
        .offset(offset)
    )
    total = db.scalar(select(func.count(Perfil.id)).where(Perfil.rol == "estudiante"))
    filas = [FilaEstudiante(perfil, int(n)) for perfil, n in db.execute(consulta).all()]
    return PaginaEstudiantes(filas, total or 0)
