"""Material de una entrega que se envía a la IA y saneamiento de la verificación técnica."""

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import Entrega

CLAVE_METRICA = re.compile(r"^[a-z0-9_]{1,40}$")
PROFUNDIDAD_MAXIMA = 8


@dataclass(frozen=True)
class Material:
    """Texto del informe, resumen del código y resultados de la verificación técnica."""

    texto_informe: str = ""
    resumen_codigo: str | None = None
    resultados_verificacion: Any = field(default_factory=dict)


CargadorMaterial = Callable[[Session, Entrega], Material]


def obtener_material(_db: Session, _entrega: Entrega) -> Material:
    """Implementación PROVISIONAL: devuelve material vacío sin descargar nada.

    Pendiente: extraer el texto del PDF desde Supabase Storage, preparar el resumen del
    código (ZIP/GitHub) y traer los resultados de la verificación de Rol 4. Con material
    vacío la evaluación termina en estado `error` (no se evalúa un informe sin texto).
    No se usa `entrega.extras` porque lo escribe el estudiante y no es confiable.
    """
    return Material()


def _limpiar(valor: Any, profundidad: int) -> Any:
    """Devuelve el valor filtrado (solo números finitos y booleanos) o None si se descarta."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if profundidad >= PROFUNDIDAD_MAXIMA:
        return None
    if isinstance(valor, dict):
        limpio = {
            clave: interno
            for clave, interno in (
                (c, _limpiar(v, profundidad + 1))
                for c, v in valor.items()
                if isinstance(c, str) and CLAVE_METRICA.fullmatch(c)
            )
            if interno is not None
        }
        return limpio or None
    if isinstance(valor, list | tuple):
        lista = [v for v in (_limpiar(x, profundidad + 1) for x in valor) if v is not None]
        return lista or None
    return None


def sanear_verificacion(datos: Any) -> dict[str, Any]:
    """Deja solo números y booleanos con claves cortas de métrica; descarta todo texto libre."""
    if not isinstance(datos, dict):
        return {}
    return _limpiar(datos, 0) or {}
