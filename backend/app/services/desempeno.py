"""Datos de desempeño de un estudiante (RF-08, RF-09): qué evaluaciones cuentan y cómo se promedia.

Reglas (todas las calcula el backend; la IA nunca aporta números):
- Solo cuentan evaluaciones `publicada`. Por cada laboratorio cuenta UNA: la publicada más
  reciente por `publicada_en` (si falta la fecha o hay empate, la de id mayor).
- Orden cronológico: número de cohorte y luego código del laboratorio (C1-01, C1-02, C2-01...).
- Promedios con aritmética exacta (`Fraction`) y redondeo ROUND_HALF_UP a 1 decimal, como nota.py.
- Dominio 0–5 de un grupo de criterios = promedio simple de `puntaje_normalizado × 5`.
- Nivel de dominio: bajo (< 3,0), medio (3,0 a < 4,0), alto (≥ 4,0).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from math import floor

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Cohorte,
    Entrega,
    Evaluacion,
    EvaluacionCriterio,
    Laboratorio,
    Perfil,
    RubricaVersion,
)
from app.services.errores import NoEncontradoError

MSG_ESTUDIANTE_NO_EXISTE = "El estudiante no existe."
UMBRAL_MEDIO = Decimal("3.0")
UMBRAL_ALTO = Decimal("4.0")
FECHA_MINIMA = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class CriterioContado:
    """Resultado de un criterio con la competencia y el nombre que tiene en su rúbrica."""

    criterio_id: str
    competencia: str
    nombre: str
    fila: EvaluacionCriterio


@dataclass(frozen=True)
class EvaluacionContada:
    """La evaluación publicada que cuenta para un laboratorio, con su contexto."""

    evaluacion: Evaluacion
    laboratorio: Laboratorio
    cohorte: Cohorte
    version: RubricaVersion
    criterios: list[CriterioContado]


def es_docente(perfil: Perfil) -> bool:
    """Docente y admin ven a cualquier estudiante."""
    return perfil.rol in ("docente", "admin")


def estudiante_visible(db: Session, estudiante_id: uuid.UUID, perfil: Perfil) -> Perfil:
    """Perfil del estudiante si el usuario puede verlo; si no, 404 (no se revela si existe)."""
    if not es_docente(perfil) and perfil.id != estudiante_id:
        raise NoEncontradoError(MSG_ESTUDIANTE_NO_EXISTE)
    estudiante = db.get(Perfil, estudiante_id)
    if estudiante is None or estudiante.rol != "estudiante":
        raise NoEncontradoError(MSG_ESTUDIANTE_NO_EXISTE)
    return estudiante


def _fecha(valor: datetime | None) -> datetime:
    """Fecha comparable en UTC (SQLite devuelve fechas sin zona)."""
    if valor is None:
        return FECHA_MINIMA
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def _criterios(version: RubricaVersion, filas: list[EvaluacionCriterio]) -> list[CriterioContado]:
    """Criterios en el orden de la rúbrica, con su competencia y nombre."""
    por_id = {f.criterio_id: f for f in filas}
    contados = []
    for criterio in version.contenido.get("criterios", []):
        fila = por_id.get(criterio.get("id"))
        if fila is not None:
            contados.append(
                CriterioContado(
                    criterio_id=fila.criterio_id,
                    competencia=str(criterio.get("competencia") or fila.criterio_id),
                    nombre=str(criterio.get("nombre") or fila.criterio_id),
                    fila=fila,
                )
            )
    return contados


def evaluaciones_contadas(db: Session, estudiante_id: uuid.UUID) -> list[EvaluacionContada]:
    """Una evaluación publicada por laboratorio (la más reciente), en orden cronológico."""
    consulta = (
        select(Evaluacion, Laboratorio, Cohorte, RubricaVersion)
        .join(Entrega, Evaluacion.entrega_id == Entrega.id)
        .join(Laboratorio, Entrega.laboratorio_id == Laboratorio.id)
        .join(Cohorte, Laboratorio.cohorte_id == Cohorte.id)
        .join(RubricaVersion, Entrega.rubrica_version_id == RubricaVersion.id)
        .where(Entrega.estudiante_id == estudiante_id, Evaluacion.estado == "publicada")
    )
    elegidas: dict[int, tuple[Evaluacion, Laboratorio, Cohorte, RubricaVersion]] = {}
    for evaluacion, laboratorio, cohorte, version in db.execute(consulta).all():
        actual = elegidas.get(laboratorio.id)
        clave = (_fecha(evaluacion.publicada_en), evaluacion.id)
        if actual is None or clave > (_fecha(actual[0].publicada_en), actual[0].id):
            elegidas[laboratorio.id] = (evaluacion, laboratorio, cohorte, version)
    ordenadas = sorted(elegidas.values(), key=lambda e: (e[2].numero, e[1].codigo))
    ids = [e[0].id for e in ordenadas]
    filas: dict[int, list[EvaluacionCriterio]] = {i: [] for i in ids}
    if ids:
        consulta_filas = (
            select(EvaluacionCriterio)
            .where(EvaluacionCriterio.evaluacion_id.in_(ids))
            .order_by(EvaluacionCriterio.id)
        )
        for fila in db.scalars(consulta_filas):
            filas[fila.evaluacion_id].append(fila)
    return [
        EvaluacionContada(ev, lab, cohorte, version, _criterios(version, filas[ev.id]))
        for ev, lab, cohorte, version in ordenadas
    ]


# ---------- Aritmética exacta ----------


def fraccion(valor: float | Decimal) -> Fraction:
    """Fraction exacta a partir del texto decimal del valor (0.85 → 17/20, sin error binario)."""
    return Fraction(str(valor))


def redondear(valor: Fraction) -> Decimal:
    """Redondea a 1 decimal con ROUND_HALF_UP (valor no negativo)."""
    return Decimal(floor(valor * 10 + Fraction(1, 2))).scaleb(-1)


def promedio(valores: Sequence[Fraction]) -> Decimal | None:
    """Promedio exacto redondeado a 1 decimal; None si no hay valores."""
    if not valores:
        return None
    return redondear(sum(valores, Fraction(0)) / len(valores))


def muestra(criterio: CriterioContado) -> Fraction | None:
    """Puntaje del criterio en escala 0–5 (normalizado × 5), o None si no tiene."""
    valor = criterio.fila.puntaje_normalizado
    return None if valor is None else fraccion(valor) * 5


def dominio(muestras: Sequence[Fraction]) -> Decimal | None:
    """Dominio 0–5: promedio de las muestras (normalizado × 5) redondeado a 1 decimal."""
    return promedio(muestras)


def nivel_dominio(valor: Decimal | None) -> str | None:
    """bajo (< 3,0), medio (3,0 a < 4,0) o alto (≥ 4,0); None sin datos."""
    if valor is None:
        return None
    if valor >= UMBRAL_ALTO:
        return "alto"
    return "medio" if valor >= UMBRAL_MEDIO else "bajo"


def numero(valor: Decimal | None) -> float | None:
    """Decimal de 1 decimal → número JSON."""
    return float(valor) if valor is not None else None
