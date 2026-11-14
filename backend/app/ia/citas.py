"""Verificación anti-alucinación de las citas del LLM contra el material (RF-05 CA3)."""

import re
import unicodedata

from pydantic import BaseModel
from rapidfuzz import fuzz

from app.ia.schemas import Evidencia

UMBRAL_SIMILITUD = 80.0
# Una cita debe cumplir AMBOS mínimos (ya normalizada): con menos texto, palabras sueltas
# como "el" o "agente" coincidirían con casi cualquier material y no prueban nada.
MIN_PALABRAS_CITA = 3
MIN_CARACTERES_CITA = 15
# Topes de CPU: la fuente se recorta a 200 000 caracteres (≈ 100 páginas) antes de normalizar;
# una cita más allá de ese punto queda no verificada. Un fragmento de más de 500 caracteres
# normalizados no es una "cita corta" (el prompt pide ~25 palabras) y se marca no verificado
# sin compararlo: es lo más simple y evita aceptar textos largos con solo un trozo real.
LIMITE_CARACTERES_FUENTE = 200_000
LIMITE_CARACTERES_FRAGMENTO = 500


class ResultadoCita(BaseModel):
    """Resultado de verificar una evidencia citada por el LLM."""

    criterio_id: str | None = None
    fragmento: str
    fuente: str
    ubicacion: str | None = None
    verificada: bool
    similitud: float


def normalizar_texto(texto: str) -> str:
    """Pasa a minúsculas, quita acentos y colapsa los espacios."""
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_acentos).strip()


def normalizar_fuente(texto_fuente: str) -> str:
    """Recorta la fuente al tope de caracteres y la normaliza (una vez por evaluación)."""
    return normalizar_texto(texto_fuente[:LIMITE_CARACTERES_FUENTE])


def cita_admisible(cita: str) -> bool:
    """Indica si una cita normalizada tiene un largo razonable para verificarse."""
    return (
        len(cita.split()) >= MIN_PALABRAS_CITA
        and MIN_CARACTERES_CITA <= len(cita) <= LIMITE_CARACTERES_FRAGMENTO
    )


def _similitud_normalizada(cita: str, fuente: str) -> float:
    """Similitud parcial (0–100) entre textos ya normalizados; 0 si no es comparable."""
    if not fuente or not cita_admisible(cita) or len(cita) > len(fuente):
        return 0.0
    return float(fuzz.partial_ratio(cita, fuente))


def similitud_cita(fragmento: str, texto_fuente: str) -> float:
    """Devuelve la similitud parcial (0–100) del fragmento dentro del texto fuente."""
    return _similitud_normalizada(normalizar_texto(fragmento), normalizar_fuente(texto_fuente))


def _resultado(
    evidencia: Evidencia, fuente_normalizada: str, criterio_id: str | None
) -> ResultadoCita:
    """Compara una evidencia con una fuente ya normalizada."""
    similitud = round(
        _similitud_normalizada(normalizar_texto(evidencia.fragmento), fuente_normalizada), 1
    )
    return ResultadoCita(
        criterio_id=criterio_id,
        fragmento=evidencia.fragmento,
        fuente=evidencia.fuente,
        ubicacion=evidencia.ubicacion,
        verificada=similitud >= UMBRAL_SIMILITUD,
        similitud=similitud,
    )


def verificar_citas_normalizadas(
    evidencias: list[Evidencia], fuente_normalizada: str, criterio_id: str | None = None
) -> list[ResultadoCita]:
    """Verifica evidencias contra una fuente ya pasada por `normalizar_fuente`."""
    return [_resultado(ev, fuente_normalizada, criterio_id) for ev in evidencias]


def verificar_cita(
    evidencia: Evidencia, texto_fuente: str, criterio_id: str | None = None
) -> ResultadoCita:
    """Marca una evidencia como verificada si su similitud con la fuente es ≥ 80."""
    return _resultado(evidencia, normalizar_fuente(texto_fuente), criterio_id)


def verificar_citas(
    evidencias: list[Evidencia], texto_fuente: str, criterio_id: str | None = None
) -> list[ResultadoCita]:
    """Verifica una lista de evidencias normalizando el texto fuente una sola vez."""
    return verificar_citas_normalizadas(evidencias, normalizar_fuente(texto_fuente), criterio_id)
