"""Configuración de IA (RF-10): consulta y cambio de proveedor, modelo y temperatura.

Nunca se devuelven ni se guardan claves ni URL: solo si están configuradas (booleanos).
Las versiones de prompt se leen de la primera línea de cada archivo, sin importar `app.ia`.
"""

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Auditoria, ConfigIA, Perfil
from app.services.errores import DatosInvalidosError
from app.services.evaluaciones import TEMPERATURA_MAXIMA, configuracion_ia

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
