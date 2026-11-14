"""Adaptador entre el backend y la IA de Rol 1 para el informe (RF-08) y el mapa (RF-09).

El backend solo conoce los tipos de este módulo (`NarrativaIA`, `MapeoIA`). Los módulos de Rol 1
(`app.ia.informe`, `app.ia.tematicas`) se importan de forma perezosa: si no existen, el informe
numérico y el mapa siguen funcionando y solo la parte de IA queda "no disponible".
La IA nunca aporta números: los traductores copian únicamente textos.
"""

import importlib
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.config import get_settings
from app.services.errores import DominioError
from app.services.evaluador_ia import ConfigProveedor, construir_proveedor

Tarea = Literal["informe", "mapeo"]

MODULOS: dict[Tarea, tuple[str, str]] = {
    "informe": ("app.ia.informe", "VERSION_PROMPT_INFORME"),
    "mapeo": ("app.ia.tematicas", "VERSION_PROMPT_MAPEO"),
}
MSG_NO_DISPONIBLE = "Esta función de IA aún no está disponible en esta versión."


class IANoDisponibleError(DominioError):
    """El módulo de IA de Rol 1 no se pudo importar."""


class GeneracionIAError(Exception):
    """La IA no produjo un resultado válido; el detalle es solo para auditoría."""

    def __init__(
        self,
        mensaje: str,
        errores: list[str] | None = None,
        respuestas_crudas: list[str] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.errores = errores or []
        self.respuestas_crudas = respuestas_crudas or []


@dataclass(frozen=True)
class AccionPlanIA:
    """Acción del plan de fortalecimiento redactada por la IA."""

    accion: str
    recurso: str
    prioridad: str
    competencia: str


@dataclass(frozen=True)
class NarrativaIA:
    """Textos del informe (sin cifras propias) más la trazabilidad."""

    competencias_desarrolladas: list[str]
    brechas: list[str]
    plan_fortalecimiento: list[AccionPlanIA]
    conclusion: str
    version_prompt: str | None = None
    proveedor: str | None = None
    modelo: str | None = None
    respuestas_crudas: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MapeoCriterioIA:
    """Temáticas (nombres exactos de la taxonomía) y conceptos de un criterio."""

    criterio_id: str
    tematicas: list[str]
    conceptos: list[str]


@dataclass(frozen=True)
class MapeoIA:
    """Mapeo criterio → temáticas de una rúbrica más la trazabilidad."""

    criterios: list[MapeoCriterioIA]
    version_prompt: str | None = None
    proveedor: str | None = None
    modelo: str | None = None
    respuestas_crudas: list[str] = field(default_factory=list)


class IAInforme(Protocol):
    """Operaciones de IA que usa el backend (los tests inyectan una versión falsa)."""

    def version_prompt(self, tarea: Tarea) -> str | None:
        """Versión del prompt de la tarea, o None si el módulo de IA no está disponible."""
        ...

    def narrativa(self, datos: dict[str, Any], config: ConfigProveedor) -> NarrativaIA:
        """Redacta la narrativa a partir de DatosDesempeno (solo cifras ya calculadas)."""
        ...

    def mapear(
        self, rubrica: dict[str, Any], tematicas: list[str], config: ConfigProveedor
    ) -> MapeoIA:
        """Asocia cada criterio de la rúbrica con temáticas de la lista."""
        ...


def _importar(nombre: str) -> Any:
    """Importa un módulo de IA o lanza IANoDisponibleError."""
    try:
        return importlib.import_module(nombre)
    except ImportError as error:
        raise IANoDisponibleError(MSG_NO_DISPONIBLE) from error


def _textos(valores: Any) -> list[str]:
    """Lista de textos (cualquier otro tipo se convierte a texto)."""
    return [str(v) for v in valores or []]


def traducir_narrativa(resultado: Any) -> NarrativaIA:
    """Traduce el ResultadoInforme de Rol 1 copiando solo textos (nunca números)."""
    informe = resultado.informe
    return NarrativaIA(
        competencias_desarrolladas=_textos(informe.competencias_desarrolladas),
        brechas=_textos(informe.brechas),
        plan_fortalecimiento=[
            AccionPlanIA(
                accion=str(a.accion),
                recurso=str(a.recurso),
                prioridad=str(a.prioridad),
                competencia=str(a.competencia),
            )
            for a in informe.plan_fortalecimiento
        ],
        conclusion=str(informe.conclusion),
        version_prompt=str(resultado.version_prompt),
        proveedor=str(resultado.proveedor),
        modelo=str(resultado.modelo),
        respuestas_crudas=_textos(resultado.respuestas_crudas),
    )


def traducir_mapeo(resultado: Any) -> MapeoIA:
    """Traduce el ResultadoMapeo de Rol 1 a MapeoIA."""
    return MapeoIA(
        criterios=[
            MapeoCriterioIA(
                criterio_id=str(m.criterio_id),
                tematicas=_textos(m.tematicas),
                conceptos=_textos(m.conceptos),
            )
            for m in resultado.mapeo.mapeos
        ],
        version_prompt=str(resultado.version_prompt),
        proveedor=str(resultado.proveedor),
        modelo=str(resultado.modelo),
        respuestas_crudas=_textos(resultado.respuestas_crudas),
    )


def _error_ia(error: Exception) -> GeneracionIAError:
    """Convierte ErrorInforme/ErrorMapeo de Rol 1 en GeneracionIAError (con su detalle)."""
    return GeneracionIAError(
        str(error),
        errores=_textos(getattr(error, "errores", [])),
        respuestas_crudas=_textos(getattr(error, "respuestas_crudas", [])),
    )


class IAInformeReal:
    """Implementación real: llama a `app.ia.informe` y `app.ia.tematicas` de Rol 1."""

    def version_prompt(self, tarea: Tarea) -> str | None:
        """Versión del prompt de Rol 1, o None si el módulo no se puede importar."""
        nombre, atributo = MODULOS[tarea]
        try:
            modulo = importlib.import_module(nombre)
        except ImportError:
            return None
        version = getattr(modulo, atributo, None)
        return str(version) if version is not None else None

    def narrativa(self, datos: dict[str, Any], config: ConfigProveedor) -> NarrativaIA:
        """Llama a generar_informe_narrativo(datos_desempeno, proveedor)."""
        modulo = _importar(MODULOS["informe"][0])
        proveedor = construir_proveedor(config, get_settings())
        try:
            resultado = modulo.generar_informe_narrativo(datos, proveedor)
        except modulo.ErrorInforme as error:
            raise _error_ia(error) from error
        return traducir_narrativa(resultado)

    def mapear(
        self, rubrica: dict[str, Any], tematicas: list[str], config: ConfigProveedor
    ) -> MapeoIA:
        """Llama a mapear_criterios_a_tematicas(rubrica, tematicas, proveedor)."""
        modulo = _importar(MODULOS["mapeo"][0])
        schemas = _importar("app.ia.schemas")
        esquema = schemas.RubricaSchema.model_validate(rubrica)
        proveedor = construir_proveedor(config, get_settings())
        try:
            resultado = modulo.mapear_criterios_a_tematicas(esquema, tematicas, proveedor)
        except modulo.ErrorMapeo as error:
            raise _error_ia(error) from error
        return traducir_mapeo(resultado)


LIMITE_MENSAJE_AUDITORIA = 4_000


def detalle_error(error: Exception) -> dict[str, Any]:
    """Detalle técnico de un fallo de IA (solo para auditoría, nunca para el cliente)."""
    detalle: dict[str, Any] = {
        "tipo": type(error).__name__,
        "mensaje": str(error)[:LIMITE_MENSAJE_AUDITORIA],
        "errores": _textos(getattr(error, "errores", [])),
        "respuestas_crudas": _textos(getattr(error, "respuestas_crudas", [])),
    }
    if error.__cause__ is not None:
        detalle["causa"] = repr(error.__cause__)[:LIMITE_MENSAJE_AUDITORIA]
    return detalle
