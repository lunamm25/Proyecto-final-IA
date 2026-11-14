"""Adaptador entre el backend y el evaluador de IA de Rol 1 (`app.ia.evaluador`).

El resto del backend solo conoce los tipos de este módulo (`SolicitudEvaluacion`,
`ResultadoIA`), no los de Rol 1. Los módulos de IA se importan de forma perezosa para
que el backend arranque aunque el evaluador aún no exista en esta versión.
"""

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.errores import DominioError

MSG_NO_DISPONIBLE = "El motor de evaluación de IA aún no está disponible en esta versión."
MSG_PROVEEDOR_DESCONOCIDO = "Proveedor de IA desconocido: '{}'. Usa gemini u openai_compat."


class EvaluadorNoDisponibleError(DominioError):
    """El módulo de IA (evaluador o proveedores) no se pudo importar."""


class ProveedorSinConfigurarError(Exception):
    """Falta la clave u otro dato del proveedor de IA en la configuración del servidor."""


class EvaluacionIAError(Exception):
    """La IA no produjo una evaluación válida; guarda el detalle solo para auditoría."""

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
class SolicitudEvaluacion:
    """Todo lo que necesita el evaluador; la verificación ya llega saneada."""

    rubrica: dict[str, Any]
    descripcion: str
    objetivos: str
    texto_informe: str
    resumen_codigo: str | None
    resultados_verificacion: dict[str, Any]
    proveedor: str
    modelo: str
    temperatura: float


@dataclass(frozen=True)
class CriterioEvaluado:
    """Nivel elegido por la IA para un criterio, con evidencias y citas verificadas."""

    criterio_id: str
    nivel_elegido: str
    justificacion: str = ""
    evidencias: list[dict[str, Any]] = field(default_factory=list)
    citas: list[dict[str, Any]] = field(default_factory=list)
    fortalezas: list[str] = field(default_factory=list)
    debilidades: list[str] = field(default_factory=list)
    recomendacion: str = ""


@dataclass(frozen=True)
class ResultadoIA:
    """Evaluación cualitativa traducida (sin nota) más la trazabilidad del prompt."""

    criterios: list[CriterioEvaluado]
    aprendizajes_identificados: list[str] = field(default_factory=list)
    como_aplico_conocimientos: str = ""
    aspectos_a_fortalecer: list[str] = field(default_factory=list)
    retroalimentacion_general: str = ""
    version_prompt: str | None = None
    respuestas_crudas: list[str] = field(default_factory=list)


Evaluador = Callable[[SolicitudEvaluacion], ResultadoIA]


class ConfigProveedor(Protocol):
    """Lo mínimo para crear un proveedor: nombre, modelo y temperatura."""

    @property
    def proveedor(self) -> str: ...

    @property
    def modelo(self) -> str: ...

    @property
    def temperatura(self) -> float: ...


def _importar(nombre: str) -> Any:
    """Importa un módulo de IA o lanza EvaluadorNoDisponibleError."""
    try:
        return importlib.import_module(nombre)
    except ImportError as error:
        raise EvaluadorNoDisponibleError(MSG_NO_DISPONIBLE) from error


def construir_proveedor(
    solicitud: ConfigProveedor, settings: Settings, timeout: float | None = None
) -> Any:
    """Crea el LLMProvider de Rol 1 según la configuración (timeout opcional, en segundos)."""
    providers = _importar("app.ia.providers")
    nombre = solicitud.proveedor.strip().lower()
    extra: dict[str, float] = {} if timeout is None else {"timeout": timeout}
    if nombre == "gemini":
        return providers.GeminiProvider(
            api_key=settings.gemini_api_key,
            modelo=solicitud.modelo,
            temperatura=solicitud.temperatura,
            **extra,
        )
    if nombre == "openai_compat":
        base_url = settings.openai_compat_base_url.strip() or providers.OLLAMA_BASE_URL
        api_key = settings.openai_compat_api_key.strip()
        if not api_key and ("localhost" in base_url or "127.0.0.1" in base_url):
            api_key = "ollama"
        return providers.OpenAICompatProvider(
            base_url=base_url,
            api_key=api_key,
            modelo=solicitud.modelo,
            temperatura=solicitud.temperatura,
            **extra,
        )
    raise ValueError(MSG_PROVEEDOR_DESCONOCIDO.format(nombre))


ProbadorConexion = Callable[[ConfigProveedor, Settings, float], None]
"""Recibe la configuración, los Settings y el timeout en segundos; lanza si falla."""


class PruebaConexionSchema(BaseModel):
    """Respuesta mínima pedida al modelo para comprobar la conexión."""

    ok: bool


PROMPT_PRUEBA = 'Prueba de conexión. Responde solo con este JSON: {"ok": true}'


def probar_conexion_ia(config: ConfigProveedor, settings: Settings, timeout: float) -> None:
    """Hace una llamada mínima al proveedor configurado; lanza excepción si falla."""
    providers = _importar("app.ia.providers")
    try:
        proveedor = construir_proveedor(config, settings, timeout=timeout)
    except providers.ErrorConfiguracionLLM as error:
        raise ProveedorSinConfigurarError(str(error)) from error
    generar_texto = getattr(proveedor, "generar_texto", None)
    if callable(generar_texto):
        generar_texto(PROMPT_PRUEBA, PruebaConexionSchema)
    else:
        proveedor.generar_json(PROMPT_PRUEBA, PruebaConexionSchema)


def _cita(cita: Any) -> dict[str, Any]:
    """Convierte un ResultadoCita de Rol 1 en un dict propio."""
    return {
        "fragmento": str(cita.fragmento),
        "fuente": str(cita.fuente),
        "ubicacion": cita.ubicacion,
        "verificada": bool(cita.verificada),
        "similitud": float(cita.similitud),
    }


def _criterio(item: Any, citas: list[dict[str, Any]]) -> CriterioEvaluado:
    """Convierte un EvaluacionCriterio de Rol 1 (se ignora cualquier campo extra)."""
    return CriterioEvaluado(
        criterio_id=str(item.criterio_id),
        nivel_elegido=str(item.nivel_elegido),
        justificacion=str(item.justificacion),
        evidencias=[
            {"fragmento": str(e.fragmento), "fuente": str(e.fuente), "ubicacion": e.ubicacion}
            for e in item.evidencias
        ],
        citas=citas,
        fortalezas=[str(f) for f in item.fortalezas],
        debilidades=[str(d) for d in item.debilidades],
        recomendacion=str(item.recomendacion),
    )


def traducir_resultado(resultado: Any) -> ResultadoIA:
    """Traduce el ResultadoEvaluacion de Rol 1 a ResultadoIA (nunca copia una nota)."""
    citas: dict[str, list[dict[str, Any]]] = {}
    for cita in resultado.citas:
        citas.setdefault(str(cita.criterio_id), []).append(_cita(cita))
    evaluacion = resultado.evaluacion
    return ResultadoIA(
        criterios=[_criterio(c, citas.get(str(c.criterio_id), [])) for c in evaluacion.criterios],
        aprendizajes_identificados=[str(a) for a in evaluacion.aprendizajes_identificados],
        como_aplico_conocimientos=str(evaluacion.como_aplico_conocimientos),
        aspectos_a_fortalecer=[str(a) for a in evaluacion.aspectos_a_fortalecer],
        retroalimentacion_general=str(evaluacion.retroalimentacion_general),
        version_prompt=str(resultado.version_prompt),
        respuestas_crudas=[str(c) for c in resultado.respuestas_crudas],
    )


def evaluar_con_ia(solicitud: SolicitudEvaluacion) -> ResultadoIA:
    """Evaluador real: llama a `app.ia.evaluador.evaluar_laboratorio` de Rol 1."""
    modulo = _importar("app.ia.evaluador")
    schemas = _importar("app.ia.schemas")
    rubrica = schemas.RubricaSchema.model_validate(solicitud.rubrica)
    proveedor = construir_proveedor(solicitud, get_settings())
    try:
        resultado = modulo.evaluar_laboratorio(
            rubrica=rubrica,
            descripcion=solicitud.descripcion,
            objetivos=solicitud.objetivos,
            texto_informe=solicitud.texto_informe,
            resumen_codigo=solicitud.resumen_codigo,
            resultados_verificacion=solicitud.resultados_verificacion,
            proveedor=proveedor,
        )
    except modulo.ErrorEvaluacion as error:
        raise EvaluacionIAError(
            str(error),
            errores=[str(e) for e in getattr(error, "errores", [])],
            respuestas_crudas=[str(c) for c in getattr(error, "respuestas_crudas", [])],
        ) from error
    return traducir_resultado(resultado)
