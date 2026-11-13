"""Cálculo determinista de la nota 0,0–5,0 a partir de la rúbrica (REQUISITOS §8).

Fórmula (sin cambios respecto a §8):
    normalizado_i = (puntaje_i - min_i) / (max_i - min_i)
    nota = Σ (ponderacion_i / 100) × normalizado_i × 5.0
    nota redondeada a 1 decimal (ROUND_HALF_UP) y acotada a [0.0, 5.0]

Decisión documentada: el nivel más bajo de cada criterio equivale a 0,0.
La aritmética se hace con `Fraction` (exacta) para que el redondeo no dependa de
errores de coma flotante; la nota se devuelve como `Decimal` (columna numeric(2,1)).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from math import floor
from typing import Any

TOLERANCIA_PONDERACION = Fraction(1, 100)
NOTA_MAXIMA = Fraction(5)


class RubricaInvalidaError(ValueError):
    """La rúbrica no permite calcular la nota de forma segura."""


class NivelInvalidoError(ValueError):
    """Los niveles elegidos no corresponden a los criterios de la rúbrica."""


@dataclass(frozen=True)
class ResultadoNota:
    """Nota final (Decimal con 1 decimal) y normalizado 0..1 por criterio_id."""

    nota: Decimal
    normalizados: dict[str, float]


def _exacto(valor: Any) -> Fraction:
    """Convierte int/float/str/Decimal a Fraction exacta usando su texto decimal."""
    return Fraction(str(valor))


def _validar_criterio(criterio: Mapping[str, Any]) -> dict[str, Fraction]:
    """Valida un criterio y devuelve sus niveles como {nombre: puntaje}."""
    cid = criterio["id"]
    niveles = {n["nombre"]: _exacto(n["puntaje"]) for n in criterio["niveles"]}
    if len(niveles) < 2:
        raise RubricaInvalidaError(
            f"El criterio '{cid}' debe tener al menos 2 niveles con nombres distintos."
        )
    if max(niveles.values()) == min(niveles.values()):
        raise RubricaInvalidaError(
            f"El criterio '{cid}' debe tener puntajes distintos entre sus niveles."
        )
    if _exacto(criterio["ponderacion"]) < 0:
        raise RubricaInvalidaError(f"El criterio '{cid}' tiene una ponderación negativa.")
    return niveles


def _validar_rubrica(criterios: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Fraction]]:
    """Valida la rúbrica completa y devuelve {criterio_id: {nombre_nivel: puntaje}}."""
    if not criterios:
        raise RubricaInvalidaError("La rúbrica no tiene criterios.")
    ids = [c["id"] for c in criterios]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        raise RubricaInvalidaError(f"Hay criterios con id repetido: {', '.join(repetidos)}.")
    suma = sum((_exacto(c["ponderacion"]) for c in criterios), Fraction(0))
    if abs(suma - 100) > TOLERANCIA_PONDERACION:
        raise RubricaInvalidaError(
            f"Las ponderaciones deben sumar 100 % (suman {float(suma):g} %)."
        )
    return {c["id"]: _validar_criterio(c) for c in criterios}


def _validar_elegidos(
    niveles_por_criterio: Mapping[str, Mapping[str, Fraction]],
    niveles_elegidos: Mapping[str, str],
) -> None:
    """Comprueba que haya un nivel válido por criterio, sin faltantes ni extras."""
    extras = sorted(set(niveles_elegidos) - set(niveles_por_criterio))
    if extras:
        raise NivelInvalidoError(f"Criterios que no existen en la rúbrica: {', '.join(extras)}.")
    for cid, niveles in niveles_por_criterio.items():
        if cid not in niveles_elegidos:
            raise NivelInvalidoError(f"Falta el nivel elegido para el criterio '{cid}'.")
        if niveles_elegidos[cid] not in niveles:
            raise NivelInvalidoError(
                f"El nivel '{niveles_elegidos[cid]}' no existe en el criterio '{cid}'."
            )


def _normalizar(niveles: Mapping[str, Fraction], nombre_nivel: str) -> Fraction:
    """Normaliza el puntaje del nivel elegido a 0..1 (mínimo = 0, máximo = 1)."""
    minimo, maximo = min(niveles.values()), max(niveles.values())
    return (niveles[nombre_nivel] - minimo) / (maximo - minimo)


def _redondear_half_up(valor: Fraction) -> Decimal:
    """Redondea a 1 decimal con ROUND_HALF_UP (valor no negativo) y acota a [0, 5]."""
    acotado = min(max(valor, Fraction(0)), NOTA_MAXIMA)
    decimas = floor(acotado * 10 + Fraction(1, 2))
    return Decimal(decimas).scaleb(-1)


def calcular_nota(
    criterios: Sequence[Mapping[str, Any]],
    niveles_elegidos: Mapping[str, str],
) -> ResultadoNota:
    """Calcula la nota 0,0–5,0 y los normalizados por criterio según §8.

    `criterios`: lista con la forma de RubricaSchema.criterios (p. ej.
    `rubrica_version.contenido["criterios"]`): id, ponderacion (%), niveles[{nombre, puntaje}].
    `niveles_elegidos`: {criterio_id: nombre_nivel} (nivel de la IA o el ajustado por el docente).
    Lanza RubricaInvalidaError o NivelInvalidoError (ambas ValueError) si no se puede calcular.
    """
    niveles_por_criterio = _validar_rubrica(criterios)
    _validar_elegidos(niveles_por_criterio, niveles_elegidos)
    normalizados = {
        cid: _normalizar(niveles, niveles_elegidos[cid])
        for cid, niveles in niveles_por_criterio.items()
    }
    total = sum(
        (_exacto(c["ponderacion"]) / 100 * normalizados[c["id"]] * 5 for c in criterios),
        Fraction(0),
    )
    return ResultadoNota(
        nota=_redondear_half_up(total),
        normalizados={cid: float(valor) for cid, valor in normalizados.items()},
    )
