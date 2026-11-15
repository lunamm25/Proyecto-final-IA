"""Tachado de secretos (claves, tokens, URL con credenciales) en textos técnicos.

Módulo único y compartido: lo usan la auditoría de errores (IA, almacén, entregas, prueba de
conexión) y la traza. Hay dos niveles:
- `tachar_secretos` / `tachar_sin_recortar`: agresivo (tacha toda URL); para mensajes de error.
- `tachar_credenciales`: solo credenciales; no altera texto normal (respuestas crudas, traza).
"""

import re
from collections.abc import Callable
from typing import Any

from app.config import Settings

# Valores de Settings que nunca deben quedar escritos si aparecen en un texto.
CAMPOS_SECRETOS = (
    "gemini_api_key",
    "openai_compat_api_key",
    "openai_compat_base_url",
    "supabase_service_key",
    "supabase_jwt_secret",
    "database_url",
)
TACHADO = "***"
LIMITE_MENSAJE_ERROR = 500
Patrones = tuple[tuple[re.Pattern[str], str], ...]
_CREDENCIALES: Patrones = (
    (re.compile(r"(?i)\bBearer\s+\S+"), f"Bearer {TACHADO}"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"), TACHADO),
    (re.compile(r"\bsk-[A-Za-z0-9_-]+"), TACHADO),
    (re.compile(r"\bAIza[A-Za-z0-9_-]+"), TACHADO),
    (re.compile(r"\bsb_secret_[A-Za-z0-9_-]+"), TACHADO),
    (re.compile(r"(?i)\b(api_key|key|token)=[^\s&;,]+"), rf"\1={TACHADO}"),
)
PATRONES_SECRETOS: Patrones = (
    (re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+"), TACHADO),
    *_CREDENCIALES,
)
PATRONES_CREDENCIALES: Patrones = (
    (re.compile(r"\b([A-Za-z][A-Za-z0-9+.-]*://)[^\s/@]+@"), rf"\1{TACHADO}@"),
    *_CREDENCIALES,
)


def _tachar(texto: str, settings: Settings, patrones: Patrones) -> str:
    """Sustituye por *** los valores exactos de Settings y luego los patrones dados."""
    valores = {str(getattr(settings, campo, "") or "").strip() for campo in CAMPOS_SECRETOS}
    for valor in sorted((v for v in valores if len(v) >= 4), key=len, reverse=True):
        texto = texto.replace(valor, TACHADO)
    for patron, reemplazo in patrones:
        texto = patron.sub(reemplazo, texto)
    return texto


def tachar_sin_recortar(texto: str, settings: Settings) -> str:
    """Igual que `tachar_secretos` pero sin recortar (el llamador decide el límite)."""
    return _tachar(texto, settings, PATRONES_SECRETOS)


def tachar_secretos(texto: str, settings: Settings) -> str:
    """Sustituye claves, tokens y URL por *** y recorta el texto (solo para auditoría)."""
    return tachar_sin_recortar(texto, settings)[:LIMITE_MENSAJE_ERROR]


def tachar_credenciales(texto: str, settings: Settings) -> str:
    """Tacha solo credenciales (claves, tokens, usuario:clave@ en URL); el resto queda igual."""
    return _tachar(texto, settings, PATRONES_CREDENCIALES)


def tachar_en_estructura(valor: Any, tachar: Callable[[str], str]) -> Any:
    """Copia de un valor JSON con `tachar` aplicado a cada texto (dict y listas, recursivo)."""
    if isinstance(valor, str):
        return tachar(valor)
    if isinstance(valor, dict):
        return {k: tachar_en_estructura(v, tachar) for k, v in valor.items()}
    if isinstance(valor, list):
        return [tachar_en_estructura(v, tachar) for v in valor]
    return valor


def detalle_error_tachado(error: Exception, settings: Settings, limite: int) -> dict[str, Any]:
    """Detalle técnico de un fallo de IA con todo texto tachado (solo para auditoría)."""

    def tachar(texto: str) -> str:
        return tachar_sin_recortar(texto, settings)[:limite]

    detalle: dict[str, Any] = {
        "tipo": type(error).__name__,
        "mensaje": tachar(str(error)),
        "errores": [tachar(str(e)) for e in getattr(error, "errores", None) or []],
        "respuestas_crudas": [
            tachar_credenciales(str(c), settings)
            for c in getattr(error, "respuestas_crudas", None) or []
        ],
    }
    if error.__cause__ is not None:
        detalle["causa"] = tachar(repr(error.__cause__))
    return detalle
