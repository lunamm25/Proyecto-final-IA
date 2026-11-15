"""Caché de resultados de IA por huella de los datos de entrada (tabla `cache_ia`, 0005).

Se reutiliza un resultado si la huella (hash de lo que se le enviaría a la IA) es la misma y la
versión del prompt no cambió. Así un GET repetido no vuelve a llamar al LLM. Los errores nunca se
guardan: el siguiente intento vuelve a llamar a la IA.

Escrituras: la auditoría de una generación correcta y su fila de caché se confirman en UN solo
commit (no quedan auditorías huérfanas). Un fallo de la base de datos al escribir nunca tumba la
petición: se hace rollback, se registra en el log (sin datos sensibles) y se devuelve igualmente
el resultado (o el respaldo).
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Auditoria, CacheIA

logger = logging.getLogger(__name__)


def huella(datos: Any) -> str:
    """SHA-256 del JSON canónico de los datos (claves ordenadas)."""
    texto = json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _fila(db: Session, tipo: str, clave: str) -> CacheIA | None:
    """Fila de la caché para (tipo, clave)."""
    return db.scalar(select(CacheIA).where(CacheIA.tipo == tipo, CacheIA.clave == clave))


def leer(
    db: Session, tipo: str, clave: str, huella_actual: str, version_prompt: str | None
) -> CacheIA | None:
    """Resultado reutilizable, o None si no hay o cambió la huella o la versión del prompt.

    Si la versión actual es None (módulo de IA no disponible) se acepta la guardada.
    """
    fila = _fila(db, tipo, clave)
    if fila is None or fila.huella != huella_actual:
        return None
    if version_prompt is not None and fila.prompt_version != version_prompt:
        return None
    return fila


def auditar(
    db: Session,
    usuario_id: Any,
    entidad: str,
    entidad_id: str,
    accion: str,
    despues: dict[str, Any],
) -> bool:
    """Registra en auditoría una generación con IA (o su error); si falla, rollback y log."""
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            entidad=entidad,
            entidad_id=entidad_id,
            accion=accion,
            despues=despues,
        )
    )
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(
            "No se pudo guardar la auditoría %s de %s/%s (%s).",
            accion,
            entidad,
            entidad_id,
            type(error).__name__,
        )
        return False
    return True


def guardar(
    db: Session,
    tipo: str,
    clave: str,
    huella_actual: str,
    contenido: Any,
    *,
    version_prompt: str | None,
    proveedor: str | None,
    modelo: str | None,
    auditoria: dict[str, Any] | None = None,
) -> datetime:
    """Inserta o reemplaza el resultado y su auditoría en un solo commit; devuelve la fecha.

    `auditoria` lleva los argumentos de `auditar` (usuario_id, entidad, entidad_id, accion,
    despues). Si otra petición guardó la misma caché a la vez, se conserva la suya y solo se
    guarda nuestra auditoría (la llamada a la IA sí ocurrió). Otro fallo: rollback y log.
    """
    ahora = datetime.now(UTC)
    fila = _fila(db, tipo, clave)
    if fila is None:
        fila = CacheIA(tipo=tipo, clave=clave)
        db.add(fila)
    fila.huella = huella_actual
    fila.contenido = contenido
    fila.prompt_version = version_prompt
    fila.proveedor = proveedor
    fila.modelo = modelo
    fila.generado_en = ahora
    if auditoria is not None:
        db.add(Auditoria(**auditoria))
    try:
        db.commit()
    except IntegrityError:
        # Otra petición guardó lo mismo a la vez: se conserva la suya.
        db.rollback()
        logger.info("Caché de IA %s/%s ya guardada por otra petición.", tipo, clave)
        if auditoria is not None:
            auditar(db, **auditoria)
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(
            "No se pudo guardar la caché de IA %s/%s ni su auditoría (%s).",
            tipo,
            clave,
            type(error).__name__,
        )
    return ahora
