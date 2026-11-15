"""Adaptador entre el backend y la extracción de rúbricas de Rol 1 (`app.ia.rubricas`).

Rol 1 expone `extraer_rubrica(texto, proveedor) -> RubricaSchema`: recibe el TEXTO del
documento (no una ruta ni bytes). El resto del backend solo conoce `RubricaExtraida` y
`ExtraccionRubricaError`. El módulo de IA se importa de forma perezosa para que el backend
arranque aunque no exista en esta versión.
"""

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.config import get_settings
from app.services.errores import ServicioNoDisponibleError
from app.services.evaluador_ia import ConfigProveedor, construir_proveedor

MODULO = "app.ia.rubricas"
# Tiempo máximo TOTAL (segundos) para extraer una rúbrica. Se pasa como timeout de cada petición
# al proveedor y, además, rubricas_ia corta la espera total con este mismo límite (la función de
# Rol 1 puede reintentar hasta 3 veces por JSON inválido). Cambia este número si hace falta.
LIMITE_EXTRAER_SEGUNDOS = 60.0
MSG_NO_DISPONIBLE = "La extracción automática de rúbricas aún no está disponible en esta versión."


class ExtractorNoDisponibleError(ServicioNoDisponibleError):
    """El módulo de extracción de Rol 1 no se pudo importar."""


class ExtraccionRubricaError(Exception):
    """La IA no produjo una rúbrica válida; el detalle es solo para auditoría."""

    def __init__(self, mensaje: str, respuestas_crudas: list[str] | None = None) -> None:
        super().__init__(mensaje)
        self.respuestas_crudas = respuestas_crudas or []


@dataclass(frozen=True)
class RubricaExtraida:
    """Rúbrica propuesta (dict con la forma de RubricaSchema) y su trazabilidad."""

    rubrica: dict[str, Any]
    version_prompt: str | None = None
    respuestas_crudas: list[str] = field(default_factory=list)


ExtractorRubrica = Callable[[str, ConfigProveedor], RubricaExtraida]
"""Recibe el texto del documento y la configuración de IA; devuelve la rúbrica propuesta."""


def _importar() -> Any:
    """Importa `app.ia.rubricas` o lanza ExtractorNoDisponibleError."""
    try:
        return importlib.import_module(MODULO)
    except ImportError as error:
        raise ExtractorNoDisponibleError(MSG_NO_DISPONIBLE) from error


def _crudas(proveedor: Any) -> list[str]:
    """Última respuesta cruda del proveedor (si la guardó)."""
    crudo = getattr(proveedor, "ultima_respuesta_cruda", None)
    return [str(crudo)] if crudo else []


def extraer_rubrica_con_ia(texto: str, config: ConfigProveedor) -> RubricaExtraida:
    """Extractor real: llama a `app.ia.rubricas.extraer_rubrica(texto, proveedor)` de Rol 1."""
    modulo = _importar()
    proveedor = construir_proveedor(config, get_settings(), timeout=LIMITE_EXTRAER_SEGUNDOS)
    try:
        resultado = modulo.extraer_rubrica(texto, proveedor)
    except Exception as error:  # fallo del proveedor, JSON inválido o texto vacío
        raise ExtraccionRubricaError(str(error), _crudas(proveedor)) from error
    version = getattr(modulo, "VERSION_PROMPT_EXTRAER_RUBRICA", None)
    return RubricaExtraida(
        rubrica=resultado.model_dump(),
        version_prompt=str(version) if version is not None else None,
        respuestas_crudas=_crudas(proveedor),
    )
