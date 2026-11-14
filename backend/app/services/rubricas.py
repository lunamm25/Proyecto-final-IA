"""Rúbricas: validador de inconsistencias (RF-03 CA2) y versionado inmutable (CA4, CA5).

Reglas bloqueantes acordadas: sin criterios, criterio sin niveles o con menos de 2,
nombres o puntajes de nivel repetidos, puntaje fuera de 0 a 5, ponderación <= 0,
suma distinta de 100, ids de criterio duplicados y, desde el 14 nov 2026, criterio
sin competencia o sin nombre y nivel sin descriptor (los exige RubricaSchema de Rol 1).
Título y orden de puntajes NO se validan por decisión del equipo.
"""

import copy
import math
import uuid
from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Laboratorio, Rubrica, RubricaVersion
from app.services.errores import (
    ConflictoError,
    NoEncontradoError,
    RubricaConInconsistenciasError,
)

TOLERANCIA_PONDERACION = 0.01  # igual que services/nota.py
PUNTAJE_MINIMO = 0.0
PUNTAJE_MAXIMO = 5.0

MSG_NO_ES_OBJETO = "La rúbrica debe ser un objeto JSON con 'titulo' y 'criterios'."
MSG_SIN_CRITERIOS = "La rúbrica no tiene criterios."
MSG_CRITERIOS_NO_LISTA = "El campo 'criterios' debe ser una lista."
MSG_LAB_NO_EXISTE = "El laboratorio no existe."
MSG_SIN_RUBRICA = "El laboratorio aún no tiene rúbrica aprobada"
MSG_CONFLICTO_VERSION = (
    "Otra persona guardó una versión de esta rúbrica al mismo tiempo. Intenta de nuevo."
)


# ---------- Validador de inconsistencias ----------


def _es_numero(valor: Any) -> bool:
    """True si es int/float finito (bool no cuenta como número)."""
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return False
    return math.isfinite(valor)


def _texto(valor: Any) -> str | None:
    """Devuelve el texto sin espacios o None si no es un texto no vacío."""
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def _fmt(numero: float) -> str:
    """Formatea un número con hasta 2 decimales y coma decimal (p. ej. 99,5)."""
    texto = f"{numero:.2f}".rstrip("0").rstrip(".")
    return "0" if texto == "-0" else texto.replace(".", ",")


def _etiqueta_criterio(criterio: dict[str, Any], posicion: int) -> str:
    """Nombra el criterio por id y nombre (o por posición si no tiene id)."""
    cid, nombre = _texto(criterio.get("id")), _texto(criterio.get("nombre"))
    base = f'Criterio "{cid}"' if cid else f"Criterio en la posición {posicion}"
    return f"{base} ({nombre})" if nombre else base


def _etiqueta_nivel(nivel: dict[str, Any], posicion: int) -> str:
    """Nombra el nivel por su nombre o por su posición."""
    nombre = _texto(nivel.get("nombre"))
    return f'el nivel "{nombre}"' if nombre else f"el nivel en la posición {posicion}"


def _errores_textos_criterio(criterio: dict[str, Any]) -> list[str]:
    """Reglas de textos obligatorios del criterio: competencia y nombre no vacíos."""
    errores = [] if _texto(criterio.get("competencia")) else ["no tiene competencia."]
    if not _texto(criterio.get("nombre")):
        errores.append("no tiene nombre.")
    return errores


def _errores_ponderacion(criterio: dict[str, Any]) -> list[str]:
    """Reglas de ponderación de un criterio: presente, numérica y mayor que 0."""
    if "ponderacion" not in criterio or criterio["ponderacion"] is None:
        return ["no tiene ponderación."]
    valor = criterio["ponderacion"]
    if not _es_numero(valor):
        return ["la ponderación debe ser un número."]
    if valor <= 0:
        return [f"la ponderación debe ser mayor que 0 (tiene {_fmt(valor)})."]
    return []


def _errores_nivel(nivel: Any, posicion: int) -> tuple[list[str], float | None, str]:
    """Valida un nivel; devuelve (errores, puntaje numérico o None, etiqueta)."""
    if not isinstance(nivel, dict):
        return [f"el nivel en la posición {posicion} debe ser un objeto JSON."], None, ""
    etiqueta = _etiqueta_nivel(nivel, posicion)
    sin_descriptor = [] if _texto(nivel.get("descriptor")) else [f"{etiqueta} no tiene descriptor."]
    errores, puntaje, etiqueta = _errores_puntaje(nivel, etiqueta)
    return sin_descriptor + errores, puntaje, etiqueta


def _errores_puntaje(nivel: dict[str, Any], etiqueta: str) -> tuple[list[str], float | None, str]:
    """Valida el puntaje de un nivel: presente, numérico y dentro de 0 a 5."""
    puntaje = nivel.get("puntaje")
    if puntaje is None:
        return [f"{etiqueta} no tiene puntaje."], None, etiqueta
    if not _es_numero(puntaje):
        detalle = etiqueta.replace("el nivel", "del nivel", 1)
        return [f"el puntaje {detalle} debe ser un número."], None, etiqueta
    if not PUNTAJE_MINIMO <= puntaje <= PUNTAJE_MAXIMO:
        return [f"{etiqueta} tiene puntaje {_fmt(puntaje)}, fuera del rango 0 a 5."], float(
            puntaje
        ), etiqueta
    return [], float(puntaje), etiqueta


def _errores_nombres_nivel(niveles: list[Any]) -> list[str]:
    """Regla de nombres de nivel sin repetir (nota.py identifica el nivel por su nombre)."""
    conteo = Counter(_texto(n.get("nombre")) for n in niveles if isinstance(n, dict))
    return [
        f'hay {veces} niveles con el nombre repetido "{nombre}".'
        for nombre, veces in conteo.items()
        if nombre and veces > 1
    ]


def _errores_niveles(criterio: dict[str, Any]) -> list[str]:
    """Reglas de los niveles: existen, al menos 2, puntajes válidos, sin repetir."""
    niveles = criterio.get("niveles")
    if niveles is None or niveles == []:
        return ["no tiene niveles de desempeño."]
    if not isinstance(niveles, list):
        return ["el campo 'niveles' debe ser una lista."]
    errores: list[str] = []
    if len(niveles) < 2:
        errores.append("debe tener al menos 2 niveles de desempeño (tiene 1).")
    errores += _errores_nombres_nivel(niveles)
    por_puntaje: dict[float, list[str]] = {}
    for posicion, nivel in enumerate(niveles, start=1):
        errores_nivel, puntaje, etiqueta = _errores_nivel(nivel, posicion)
        errores.extend(errores_nivel)
        if puntaje is not None:
            por_puntaje.setdefault(puntaje, []).append(etiqueta.removeprefix("el "))
    for puntaje, nombres in por_puntaje.items():
        if len(nombres) > 1:
            errores.append(
                f"hay niveles con el puntaje repetido {_fmt(puntaje)} ({', '.join(nombres)})."
            )
    return errores


def _error_suma(criterios: list[dict[str, Any]]) -> list[str]:
    """Regla de suma 100 % con las ponderaciones numéricas disponibles."""
    numericas = [c.get("ponderacion") for c in criterios if _es_numero(c.get("ponderacion"))]
    suma = math.fsum(numericas)
    if abs(suma - 100) <= TOLERANCIA_PONDERACION:
        return []
    mensaje = f"Las ponderaciones suman {_fmt(suma)} % y deben sumar 100 %"
    sin_valor = len(criterios) - len(numericas)
    if sin_valor:
        plural = "criterio" if sin_valor == 1 else "criterios"
        mensaje += f" (sin contar {sin_valor} {plural} con ponderación no válida)"
    return [mensaje + "."]


def _errores_ids(criterios: list[dict[str, Any]]) -> list[str]:
    """Regla de ids duplicados (un mensaje por id)."""
    conteo = Counter(_texto(c.get("id")) for c in criterios)
    return [
        f'Hay {veces} criterios con el id duplicado "{cid}".'
        for cid, veces in conteo.items()
        if cid and veces > 1
    ]


def validar_rubrica(rubrica: Any) -> list[str]:
    """Lista todas las inconsistencias de la rúbrica; lista vacía = válida. Nunca lanza."""
    if not isinstance(rubrica, dict):
        return [MSG_NO_ES_OBJETO]
    criterios = rubrica.get("criterios")
    if criterios is None or criterios == []:
        return [MSG_SIN_CRITERIOS]
    if not isinstance(criterios, list):
        return [MSG_CRITERIOS_NO_LISTA]
    errores: list[str] = []
    validos: list[dict[str, Any]] = []
    for posicion, criterio in enumerate(criterios, start=1):
        if not isinstance(criterio, dict):
            errores.append(f"Criterio en la posición {posicion}: debe ser un objeto JSON.")
            continue
        validos.append(criterio)
        etiqueta = _etiqueta_criterio(criterio, posicion)
        propios = [] if _texto(criterio.get("id")) else ["no tiene id."]
        propios += _errores_textos_criterio(criterio)
        propios += _errores_ponderacion(criterio) + _errores_niveles(criterio)
        errores.extend(f"{etiqueta}: {e}" for e in propios)
    errores += _errores_ids(validos)
    if validos:
        errores += _error_suma(validos)
    return list(dict.fromkeys(errores))


# ---------- Versionado ----------


def _laboratorio_o_404(db: Session, laboratorio_id: int) -> Laboratorio:
    """Devuelve el laboratorio o lanza NoEncontradoError."""
    laboratorio = db.get(Laboratorio, laboratorio_id)
    if laboratorio is None:
        raise NoEncontradoError(MSG_LAB_NO_EXISTE)
    return laboratorio


def obtener_version_vigente(db: Session, laboratorio_id: int) -> RubricaVersion | None:
    """Versión vigente: la de mayor número con estado `aprobada` (o None)."""
    consulta = (
        select(RubricaVersion)
        .join(Rubrica, RubricaVersion.rubrica_id == Rubrica.id)
        .where(Rubrica.laboratorio_id == laboratorio_id, RubricaVersion.estado == "aprobada")
        .order_by(RubricaVersion.version.desc())
        .limit(1)
    )
    return db.scalar(consulta)


def leer_version_vigente(db: Session, laboratorio_id: int) -> RubricaVersion:
    """Versión vigente o NoEncontradoError (laboratorio inexistente o sin rúbrica)."""
    _laboratorio_o_404(db, laboratorio_id)
    version = obtener_version_vigente(db, laboratorio_id)
    if version is None:
        raise NoEncontradoError(MSG_SIN_RUBRICA)
    return version


def _rubrica_del_laboratorio(db: Session, laboratorio_id: int) -> Rubrica:
    """Obtiene (o crea sin confirmar) la fila `rubricas` del laboratorio."""
    rubrica = db.scalar(select(Rubrica).where(Rubrica.laboratorio_id == laboratorio_id))
    if rubrica is None:
        rubrica = Rubrica(laboratorio_id=laboratorio_id)
        db.add(rubrica)
        db.flush()
    return rubrica


def guardar_version(
    db: Session, laboratorio_id: int, contenido: Any, creada_por: uuid.UUID
) -> RubricaVersion:
    """Valida y guarda una versión nueva aprobada (máximo + 1); las anteriores no cambian."""
    _laboratorio_o_404(db, laboratorio_id)
    inconsistencias = validar_rubrica(contenido)
    if inconsistencias:
        raise RubricaConInconsistenciasError(inconsistencias)
    try:
        rubrica = _rubrica_del_laboratorio(db, laboratorio_id)
        ultima = db.scalar(
            select(func.max(RubricaVersion.version)).where(RubricaVersion.rubrica_id == rubrica.id)
        )
        version = RubricaVersion(
            rubrica_id=rubrica.id,
            version=(ultima or 0) + 1,
            estado="aprobada",
            contenido=copy.deepcopy(contenido),
            creada_por=creada_por,
        )
        db.add(version)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictoError(MSG_CONFLICTO_VERSION) from None
    db.refresh(version)
    return version
