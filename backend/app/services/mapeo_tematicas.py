"""Mapeo criterio → temáticas (RF-09 CA2) con caché por versión de rúbrica.

El mapeo depende solo de la rúbrica (versión inmutable) y de la taxonomía de temáticas, así que se
genera con IA una sola vez por `rubrica_version_id` y se guarda en `cache_ia` (huella = lista de
temáticas). Si la IA no está disponible o falla, esa versión queda sin mapeo (None) y quien lo use
agrupa por competencia. El detalle de cualquier fallo va solo a auditoría.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Perfil, RubricaVersion, Tematica
from app.services import cache_ia
from app.services.evaluador_ia import ConfigProveedor
from app.services.informe_ia import IAInforme, IANoDisponibleError, MapeoIA, detalle_error

logger = logging.getLogger(__name__)

TIPO = "mapeo_tematicas"


@dataclass(frozen=True)
class MapeoCriterio:
    """Temáticas (ids de la taxonomía) y conceptos asociados a un criterio."""

    tematica_ids: list[int]
    conceptos: list[str]


MapeoVersion = dict[str, MapeoCriterio]


def slug(texto: str) -> str:
    """Identificador estable: minúsculas, sin acentos, palabras separadas por guiones."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    ascii_ = "".join(c for c in sin_acentos if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_).strip("-") or "x"


def _clave_nombre(nombre: str) -> str:
    """Clave para comparar nombres de temáticas (sin mayúsculas, acentos ni espacios extra)."""
    return " ".join(slug(nombre).split("-"))


def cargar_taxonomia(db: Session) -> dict[int, Tematica]:
    """Temáticas por id, en el orden de la taxonomía (id)."""
    return {t.id: t for t in db.scalars(select(Tematica).order_by(Tematica.id))}


def ancestros(tematica_id: int, taxonomia: dict[int, Tematica]) -> list[int]:
    """Ids de los padres de la temática, del más general al más cercano (sin ciclos)."""
    cadena: list[int] = []
    actual = taxonomia.get(tematica_id)
    while actual is not None and actual.padre_id in taxonomia and actual.padre_id not in cadena:
        if actual.padre_id == tematica_id:
            break
        cadena.append(actual.padre_id)
        actual = taxonomia[actual.padre_id]
    return list(reversed(cadena))


def _a_json(mapeo: MapeoIA, taxonomia: dict[int, Tematica]) -> dict[str, Any]:
    """Mapeo de la IA con temáticas convertidas a ids (los nombres desconocidos se ignoran)."""
    por_nombre = {_clave_nombre(t.nombre): t.id for t in taxonomia.values()}
    contenido: dict[str, Any] = {}
    for item in mapeo.criterios:
        ids: list[int] = []
        for nombre in item.tematicas:
            tid = por_nombre.get(_clave_nombre(nombre))
            if tid is not None and tid not in ids:
                ids.append(tid)
        conceptos = [c.strip() for c in item.conceptos if c.strip()]
        contenido[item.criterio_id] = {"tematica_ids": ids, "conceptos": conceptos}
    return contenido


def _desde_json(contenido: dict[str, Any], taxonomia: dict[int, Tematica]) -> MapeoVersion:
    """Mapeo guardado, descartando temáticas que ya no existan."""
    return {
        str(cid): MapeoCriterio(
            tematica_ids=[int(t) for t in item.get("tematica_ids", []) if int(t) in taxonomia],
            conceptos=[str(c) for c in item.get("conceptos", [])],
        )
        for cid, item in contenido.items()
    }


def _generar(
    db: Session,
    version: RubricaVersion,
    nombres: list[str],
    taxonomia: dict[int, Tematica],
    contexto: tuple[IAInforme, ConfigProveedor, Perfil, str],
) -> MapeoVersion | None:
    """Llama a la IA, audita y guarda en caché; None si falla."""
    ia, config, perfil, huella = contexto
    try:
        mapeo = ia.mapear(version.contenido, nombres, config)
    except IANoDisponibleError:
        return None
    except Exception as error:  # cualquier fallo de la IA: mapa agrupado por competencia
        logger.warning("Mapeo de temáticas falló para la versión %s.", version.id)
        cache_ia.auditar(
            db, perfil.id, "rubrica_versiones", str(version.id), "mapear_tematicas_ia_error",
            detalle_error(error),
        )
        return None
    contenido = _a_json(mapeo, taxonomia)
    cache_ia.auditar(
        db,
        perfil.id,
        "rubrica_versiones",
        str(version.id),
        "mapear_tematicas_ia",
        {
            "proveedor": mapeo.proveedor,
            "modelo": mapeo.modelo,
            "version_prompt": mapeo.version_prompt,
            "respuestas_crudas": mapeo.respuestas_crudas,
            "mapeo": contenido,
        },
    )
    cache_ia.guardar(
        db, TIPO, str(version.id), huella, contenido,
        version_prompt=mapeo.version_prompt, proveedor=mapeo.proveedor, modelo=mapeo.modelo,
    )
    return _desde_json(contenido, taxonomia)


def obtener_mapeos(
    db: Session,
    versiones: list[RubricaVersion],
    taxonomia: dict[int, Tematica],
    ia: IAInforme,
    config: ConfigProveedor,
    perfil: Perfil,
) -> dict[int, MapeoVersion | None]:
    """Mapeo por versión de rúbrica: de la caché si sirve; si no, con IA. None = sin mapeo."""
    unicas = list({v.id: v for v in versiones}.values())
    if not taxonomia:
        return {v.id: None for v in unicas}
    nombres = [t.nombre for t in taxonomia.values()]
    huella = cache_ia.huella(sorted(nombres))
    version_prompt = ia.version_prompt("mapeo")
    resultado: dict[int, MapeoVersion | None] = {}
    for version in unicas:
        fila = cache_ia.leer(db, TIPO, str(version.id), huella, version_prompt)
        if fila is not None:
            resultado[version.id] = _desde_json(fila.contenido, taxonomia)
        elif version_prompt is None:
            resultado[version.id] = None
        else:
            contexto = (ia, config, perfil, huella)
            resultado[version.id] = _generar(db, version, nombres, taxonomia, contexto)
    return resultado
