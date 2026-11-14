"""Configuración de IA (RF-10): consulta, cambio y prueba de conexión del proveedor.

Nunca se devuelven ni se guardan claves ni URL: solo si están configuradas (booleanos).
Las versiones de prompt se leen de la primera línea de cada archivo, sin importar `app.ia`.
"""

import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Auditoria, ConfigIA, Perfil
from app.services.errores import DatosInvalidosError
from app.services.evaluaciones import TEMPERATURA_MAXIMA, ConfigEvaluacion, configuracion_ia
from app.services.evaluador_ia import ProbadorConexion, ProveedorSinConfigurarError

# Modelos de Gemini que el admin puede elegir. Para añadir uno, agrégalo a esta tupla.
MODELOS_GEMINI: tuple[str, ...] = ("gemini-3.5-flash-lite", "gemini-2.5-flash")

# Proveedores elegibles desde el panel (nombre que espera el código → etiqueta para la interfaz).
PROVEEDORES: dict[str, str] = {
    "gemini": "Google Gemini",
    "openai_compat": "OpenAI-compatible (Ollama, Groq, OpenRouter)",
}

PATRON_MODELO = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}")
CARPETA_PROMPTS = Path(__file__).resolve().parents[1] / "ia" / "prompts"
ENTIDAD_AUDITORIA = "config_ia"
ACCION_CAMBIAR = "cambiar_config_ia"

MSG_PROVEEDOR_NO_VALIDO = "Proveedor de IA no válido. Usa: gemini u openai_compat."
MSG_MODELO_FORMATO = (
    "El nombre del modelo no es válido: usa solo letras, números y . _ : / - "
    "(sin espacios, máximo 100 caracteres)."
)
MSG_MODELO_NO_PERMITIDO = "Modelo no permitido para {}. Opciones: {}."
MSG_SIN_MODELOS_OPENAI = (
    "No hay modelos configurados para openai_compat; define OPENAI_COMPAT_MODELOS en el servidor."
)


@dataclass(frozen=True)
class EstadoConfigIA:
    """Configuración vigente y metadatos que devuelve la API (sin secretos)."""

    proveedor: str
    modelo: str
    temperatura: float
    origen: str
    modelo_permitido: bool
    actualizado_por: dict[str, Any] | None
    actualizado_en: Any
    temperatura_maxima: float
    claves: dict[str, bool]
    proveedores_permitidos: list[dict[str, Any]]
    versiones_prompt: dict[str, str | None]


def es_nombre_modelo_valido(nombre: str) -> bool:
    """True si el nombre cumple el patrón seguro (sin espacios ni caracteres raros)."""
    return PATRON_MODELO.fullmatch(nombre) is not None


def _modelos_openai(settings: Settings) -> list[str]:
    """Modelos de OPENAI_COMPAT_MODELOS válidos; si no hay, LLM_MODEL cuando es el proveedor."""
    modelos: list[str] = []
    for nombre in settings.openai_compat_modelos.split(","):
        nombre = nombre.strip()
        if es_nombre_modelo_valido(nombre) and nombre not in modelos:
            modelos.append(nombre)
    if modelos:
        return modelos
    modelo_env = settings.llm_model.strip()
    if settings.llm_provider.strip().lower() == "openai_compat" and es_nombre_modelo_valido(
        modelo_env
    ):
        return [modelo_env]
    return []


def modelos_permitidos(settings: Settings) -> dict[str, list[str]]:
    """Lista blanca de modelos por proveedor."""
    return {"gemini": list(MODELOS_GEMINI), "openai_compat": _modelos_openai(settings)}


def _version_de(ruta: Path) -> str | None:
    """Versión de la primera línea `version: x.y` del prompt, o None si no la tiene."""
    try:
        with ruta.open(encoding="utf-8") as archivo:
            primera = archivo.readline().strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not primera.lower().startswith("version:"):
        return None
    return primera.split(":", 1)[1].strip() or None


def versiones_prompt() -> dict[str, str | None]:
    """Versión de cada prompt `*.md` de la carpeta de prompts (solo lectura)."""
    if not CARPETA_PROMPTS.is_dir():
        return {}
    return {ruta.stem: _version_de(ruta) for ruta in sorted(CARPETA_PROMPTS.glob("*.md"))}


def _claves_configuradas(settings: Settings) -> dict[str, bool]:
    """Solo indica si cada secreto está definido; nunca su valor."""
    return {
        "gemini_api_key_configurada": bool(settings.gemini_api_key.strip()),
        "openai_compat_api_key_configurada": bool(settings.openai_compat_api_key.strip()),
        "openai_compat_base_url_configurada": bool(settings.openai_compat_base_url.strip()),
    }


def _actualizador(db: Session, fila: ConfigIA | None) -> dict[str, Any] | None:
    """Id y nombre de quien cambió la configuración por última vez (o None)."""
    if fila is None or fila.actualizado_por is None:
        return None
    perfil = db.get(Perfil, fila.actualizado_por)
    return {"id": fila.actualizado_por, "nombre": perfil.nombre if perfil else None}


def obtener_config(db: Session, settings: Settings) -> EstadoConfigIA:
    """Configuración vigente (fila 1 o variables LLM_*) con claves y listas permitidas."""
    fila = db.get(ConfigIA, 1)
    vigente = configuracion_ia(db, settings)
    permitidos = modelos_permitidos(settings)
    return EstadoConfigIA(
        proveedor=vigente.proveedor,
        modelo=vigente.modelo,
        temperatura=vigente.temperatura,
        origen="base_de_datos" if fila is not None else "entorno",
        modelo_permitido=vigente.modelo in permitidos.get(vigente.proveedor, []),
        actualizado_por=_actualizador(db, fila),
        actualizado_en=fila.actualizado_en if fila is not None else None,
        temperatura_maxima=TEMPERATURA_MAXIMA,
        claves=_claves_configuradas(settings),
        proveedores_permitidos=[
            {"proveedor": nombre, "etiqueta": etiqueta, "modelos": permitidos[nombre]}
            for nombre, etiqueta in PROVEEDORES.items()
        ],
        versiones_prompt=versiones_prompt(),
    )


def _validar(proveedor: str, modelo: str, settings: Settings) -> tuple[str, str]:
    """Normaliza y valida proveedor y modelo contra la lista blanca (422 si no)."""
    proveedor = proveedor.strip().lower()
    if proveedor not in PROVEEDORES:
        raise DatosInvalidosError(MSG_PROVEEDOR_NO_VALIDO)
    modelo = modelo.strip()
    if not es_nombre_modelo_valido(modelo):
        raise DatosInvalidosError(MSG_MODELO_FORMATO)
    permitidos = modelos_permitidos(settings)[proveedor]
    if not permitidos:
        raise DatosInvalidosError(MSG_SIN_MODELOS_OPENAI)
    if modelo not in permitidos:
        raise DatosInvalidosError(MSG_MODELO_NO_PERMITIDO.format(proveedor, ", ".join(permitidos)))
    return proveedor, modelo


def _valores(proveedor: str, modelo: str, temperatura: float) -> dict[str, Any]:
    """Valores de configuración tal como se guardan en auditoría."""
    return {"proveedor": proveedor, "modelo": modelo, "temperatura": temperatura}


def cambiar_config(
    db: Session,
    actor: Perfil,
    proveedor: str,
    modelo: str,
    temperatura: float,
    settings: Settings,
) -> EstadoConfigIA:
    """Guarda la configuración y la audita en la misma transacción (igual → sin cambios)."""
    proveedor, modelo = _validar(proveedor, modelo, settings)
    fila = db.get(ConfigIA, 1, with_for_update=True)
    nuevos = _valores(proveedor, modelo, temperatura)
    if fila is None:
        vigente = configuracion_ia(db, settings)
        antes = {
            "origen": "entorno",
            **_valores(vigente.proveedor, vigente.modelo, vigente.temperatura),
        }
        fila = ConfigIA(id=1, **nuevos)
        db.add(fila)
    elif (
        fila.proveedor == proveedor
        and fila.modelo == modelo
        and math.isclose(fila.temperatura, temperatura, abs_tol=1e-9)
    ):
        return obtener_config(db, settings)
    else:
        antes = _valores(fila.proveedor, fila.modelo, fila.temperatura)
        fila.proveedor, fila.modelo, fila.temperatura = proveedor, modelo, temperatura
    fila.actualizado_por = actor.id
    db.add(
        Auditoria(
            usuario_id=actor.id,
            entidad=ENTIDAD_AUDITORIA,
            entidad_id="1",
            accion=ACCION_CAMBIAR,
            antes=antes,
            despues=nuevos,
        )
    )
    db.commit()
    db.refresh(fila)
    return obtener_config(db, settings)


# ---------- Prueba de conexión (RF-10 CA2) ----------

LIMITE_PRUEBA_SEGUNDOS = 10.0
LIMITE_MENSAJE_ERROR = 500
ACCION_PROBAR = "probar_config_ia"
MSG_PRUEBA_OK = "Conexión correcta con el proveedor de IA."
MSG_PRUEBA_FALLO = (
    "No se pudo conectar con el proveedor de IA. Revisa la configuración del servidor."
)
MSG_PRUEBA_SIN_CLAVE = "Falta configurar la clave del proveedor en el servidor."
MSG_PRUEBA_TIEMPO = "El proveedor de IA no respondió a tiempo ({:g} s)."
MENSAJES_PRUEBA = {
    "ok": MSG_PRUEBA_OK,
    "fallo": MSG_PRUEBA_FALLO,
    "sin_clave": MSG_PRUEBA_SIN_CLAVE,
}
HOSTS_LOCALES = ("localhost", "127.0.0.1")
# Valores de Settings que nunca deben quedar escritos en auditoría si aparecen en un error.
CAMPOS_SECRETOS = (
    "gemini_api_key",
    "openai_compat_api_key",
    "openai_compat_base_url",
    "supabase_service_key",
    "supabase_jwt_secret",
    "database_url",
)
TACHADO = "***"
PATRONES_SECRETOS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+"), TACHADO),
    (re.compile(r"(?i)\bBearer\s+\S+"), f"Bearer {TACHADO}"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"), TACHADO),
    (re.compile(r"\bsk-[A-Za-z0-9_-]+"), TACHADO),
    (re.compile(r"\bAIza[A-Za-z0-9_-]+"), TACHADO),
    (re.compile(r"\bsb_secret_[A-Za-z0-9_-]+"), TACHADO),
    (re.compile(r"(?i)\b(api_key|key|token)=[^\s&;,]+"), rf"\1={TACHADO}"),
)


@dataclass(frozen=True)
class ResultadoPrueba:
    """Resultado de probar la conexión (sin claves ni texto crudo del error)."""

    ok: bool
    proveedor: str
    modelo: str
    latencia_ms: int | None
    mensaje: str


def mensaje_tiempo_agotado(limite: float) -> str:
    """Mensaje para el usuario cuando el proveedor no responde dentro del límite."""
    return MSG_PRUEBA_TIEMPO.format(limite)


def tachar_secretos(texto: str, settings: Settings) -> str:
    """Sustituye claves, tokens y URL por *** y recorta el texto (solo para auditoría)."""
    valores = {str(getattr(settings, campo, "") or "").strip() for campo in CAMPOS_SECRETOS}
    for valor in sorted((v for v in valores if len(v) >= 4), key=len, reverse=True):
        texto = texto.replace(valor, TACHADO)
    for patron, reemplazo in PATRONES_SECRETOS:
        texto = patron.sub(reemplazo, texto)
    return texto[:LIMITE_MENSAJE_ERROR]


def _falta_clave(proveedor: str, settings: Settings) -> str | None:
    """Qué variable falta para usar el proveedor (sin revelar valores), o None."""
    if proveedor == "gemini" and not settings.gemini_api_key.strip():
        return "Falta GEMINI_API_KEY."
    if proveedor == "openai_compat" and not settings.openai_compat_api_key.strip():
        url = settings.openai_compat_base_url.strip()
        if url and not any(host in url for host in HOSTS_LOCALES):
            return "Falta OPENAI_COMPAT_API_KEY para una URL base remota."
    return None


def _milisegundos(inicio: float) -> int:
    """Milisegundos transcurridos desde `inicio` (time.monotonic)."""
    return round((time.monotonic() - inicio) * 1000)


def _ejecutar_con_limite(
    probador: ProbadorConexion, config: ConfigEvaluacion, settings: Settings, limite: float
) -> tuple[str, int | None, Exception | None]:
    """Llama al probador en un hilo y espera como máximo `limite` segundos en total."""
    ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="probar-ia")
    inicio = time.monotonic()
    futuro = ejecutor.submit(probador, config, settings, limite)
    try:
        futuro.result(timeout=limite)
    except TimeoutError as error:
        return "tiempo_agotado", round(limite * 1000), error
    except ProveedorSinConfigurarError as error:
        return "sin_clave", None, error
    except Exception as error:  # cualquier fallo del proveedor se resume como "fallo"
        return "fallo", _milisegundos(inicio), error
    finally:
        ejecutor.shutdown(wait=False, cancel_futures=True)
    return "ok", _milisegundos(inicio), None


def _detalle_error(
    resultado: str, error: Exception, settings: Settings, limite: float
) -> dict[str, str]:
    """Tipo y mensaje tachado del error, solo para auditoría."""
    if resultado == "tiempo_agotado":
        return {"tipo": "TimeoutError", "mensaje": f"Sin respuesta en {limite:g} s."}
    return {"tipo": type(error).__name__, "mensaje": tachar_secretos(str(error), settings)}


def probar_conexion(
    db: Session,
    actor: Perfil,
    settings: Settings,
    probador: ProbadorConexion,
    limite: float = LIMITE_PRUEBA_SEGUNDOS,
) -> ResultadoPrueba:
    """Prueba la configuración guardada y deja el resultado en auditoría (siempre)."""
    config = configuracion_ia(db, settings)
    falta = _falta_clave(config.proveedor.strip().lower(), settings)
    error: dict[str, str] | None
    if falta is not None:
        resultado, latencia = "sin_clave", None
        error = {"tipo": "ClaveNoConfigurada", "mensaje": falta}
    else:
        resultado, latencia, excepcion = _ejecutar_con_limite(probador, config, settings, limite)
        error = (
            None if excepcion is None else _detalle_error(resultado, excepcion, settings, limite)
        )
    ok = resultado == "ok"
    db.add(
        Auditoria(
            usuario_id=actor.id,
            entidad=ENTIDAD_AUDITORIA,
            entidad_id="1",
            accion=ACCION_PROBAR,
            despues={
                "ok": ok,
                "proveedor": config.proveedor,
                "modelo": config.modelo,
                "latencia_ms": latencia,
                "resultado": resultado,
                "error": error,
            },
        )
    )
    db.commit()
    mensaje = MENSAJES_PRUEBA.get(resultado) or mensaje_tiempo_agotado(limite)
    return ResultadoPrueba(ok, config.proveedor, config.modelo, latencia, mensaje)
