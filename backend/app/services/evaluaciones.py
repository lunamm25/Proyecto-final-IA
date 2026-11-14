"""Evaluación de entregas con IA (RF-05): lanzamiento, tarea de fondo y consulta por rol.

Flujo: POST crea la evaluación en `procesando` → la tarea de fondo llama al evaluador →
el backend valida los niveles, calcula la nota con `nota.py` y la deja en `borrador`.
Cualquier fallo deja la evaluación en `error` con un mensaje genérico; el detalle (incluidas
las respuestas crudas del LLM) va solo a `auditoria`.
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    Auditoria,
    ConfigIA,
    Entrega,
    Evaluacion,
    EvaluacionCriterio,
    Laboratorio,
    Perfil,
    RubricaVersion,
)
from app.services.errores import (
    ConflictoError,
    DominioError,
    NoEncontradoError,
    ProhibidoError,
)
from app.services.evaluador_ia import Evaluador, ResultadoIA, SolicitudEvaluacion
from app.services.material import CargadorMaterial, sanear_verificacion
from app.services.nota import calcular_nota
from app.services.rubricas import validar_rubrica

logger = logging.getLogger(__name__)

TEMPERATURA_MAXIMA = 0.2
LIMITE_MENSAJE_AUDITORIA = 4_000

MSG_ENTREGA_NO_EXISTE = "La entrega no existe."
MSG_EVALUACION_NO_EXISTE = "La evaluación no existe."
MSG_EN_CURSO = "Ya hay una evaluación en curso para esta entrega."
MSG_SIN_VERSION = "La entrega no tiene una versión de rúbrica aprobada; no se puede evaluar."
MSG_RUBRICA_INCONSISTENTE = (
    "La versión de la rúbrica de esta entrega tiene inconsistencias; no se puede evaluar: {}"
)
MSG_PENDIENTE = "La evaluación está pendiente de revisión docente."
MSG_ERROR_GENERICO = (
    "No se pudo completar la evaluación automática. Intenta de nuevo o contacta al docente."
)
MSG_SIN_TEXTO = "La entrega no tiene texto de informe disponible para evaluar."


class PendienteRevisionError(ProhibidoError):
    """El estudiante pide una evaluación propia que aún no está publicada (HTTP 403)."""


class ResultadoIncoherenteError(Exception):
    """La respuesta del evaluador no coincide con los criterios/niveles de la rúbrica."""


@dataclass(frozen=True)
class ConfigEvaluacion:
    """Proveedor, modelo y temperatura (≤ 0.2) con los que se evalúa."""

    proveedor: str
    modelo: str
    temperatura: float


@dataclass(frozen=True)
class DetalleEvaluacion:
    """Evaluación con sus criterios y su versión de rúbrica, y si la ve un estudiante."""

    evaluacion: Evaluacion
    criterios: list[EvaluacionCriterio]
    rubrica_version: RubricaVersion | None
    vista_estudiante: bool


# ---------- Lanzamiento (petición HTTP) ----------


def _es_docente(perfil: Perfil) -> bool:
    """Docente y admin pueden ver y evaluar cualquier entrega."""
    return perfil.rol in ("docente", "admin")


def _entrega_visible(db: Session, entrega_id: int, perfil: Perfil) -> Entrega:
    """Entrega si existe y el usuario puede verla; si no, 404 (no se revela que existe)."""
    entrega = db.get(Entrega, entrega_id)
    if entrega is None or not (_es_docente(perfil) or entrega.estudiante_id == perfil.id):
        raise NoEncontradoError(MSG_ENTREGA_NO_EXISTE)
    return entrega


def _version_evaluable(db: Session, entrega: Entrega) -> RubricaVersion:
    """Versión de rúbrica de la entrega, aprobada y sin inconsistencias (o 409)."""
    version = db.get(RubricaVersion, entrega.rubrica_version_id)
    if version is None or version.estado != "aprobada":
        raise ConflictoError(MSG_SIN_VERSION)
    inconsistencias = validar_rubrica(version.contenido)
    if inconsistencias:
        raise ConflictoError(MSG_RUBRICA_INCONSISTENTE.format(" ".join(inconsistencias)))
    return version


def _hay_evaluacion_en_curso(db: Session, entrega_id: int) -> bool:
    """True si la entrega ya tiene una evaluación en `procesando`."""
    consulta = select(Evaluacion.id).where(
        Evaluacion.entrega_id == entrega_id, Evaluacion.estado == "procesando"
    )
    return db.scalar(consulta.limit(1)) is not None


def configuracion_ia(db: Session, settings: Settings) -> ConfigEvaluacion:
    """Config de `config_ia` (fila 1) o, si no existe, la de las variables LLM_*."""
    fila = db.get(ConfigIA, 1)
    if fila is not None:
        proveedor, modelo, temperatura = fila.proveedor, fila.modelo, fila.temperatura
    else:
        proveedor, modelo = settings.llm_provider, settings.llm_model
        temperatura = settings.llm_temperature
    temperatura = min(max(float(temperatura), 0.0), TEMPERATURA_MAXIMA)
    return ConfigEvaluacion(proveedor, modelo, temperatura)


def lanzar_evaluacion(
    db: Session, entrega_id: int, perfil: Perfil, settings: Settings
) -> Evaluacion:
    """Valida permisos y rúbrica, y crea la evaluación en `procesando` (commit incluido)."""
    entrega = _entrega_visible(db, entrega_id, perfil)
    _version_evaluable(db, entrega)
    if _hay_evaluacion_en_curso(db, entrega.id):
        raise ConflictoError(MSG_EN_CURSO)
    config = configuracion_ia(db, settings)
    evaluacion = Evaluacion(
        entrega_id=entrega.id,
        estado="procesando",
        proveedor=config.proveedor,
        modelo=config.modelo,
        temperatura=config.temperatura,
    )
    db.add(evaluacion)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictoError(MSG_EN_CURSO) from None
    db.refresh(evaluacion)
    return evaluacion


# ---------- Tarea de fondo ----------


def _validar_resultado(criterios: list[dict[str, Any]], resultado: ResultadoIA) -> dict[str, str]:
    """Comprueba criterios completos, sin extras ni repetidos y niveles existentes (§7)."""
    recibidos = [c.criterio_id for c in resultado.criterios]
    esperados = [c["id"] for c in criterios]
    if len(recibidos) != len(set(recibidos)) or set(recibidos) != set(esperados):
        raise ResultadoIncoherenteError(
            f"Criterios recibidos {recibidos} no coinciden con la rúbrica {esperados}."
        )
    niveles = {c["id"]: {n["nombre"] for n in c["niveles"]} for c in criterios}
    elegidos = {c.criterio_id: c.nivel_elegido for c in resultado.criterios}
    invalidos = [cid for cid, nivel in elegidos.items() if nivel not in niveles[cid]]
    if invalidos:
        raise ResultadoIncoherenteError(f"Niveles inexistentes en los criterios {invalidos}.")
    return elegidos


def _resultado_json(resultado: ResultadoIA) -> dict[str, Any]:
    """Evaluación validada para la columna `resultado` (sin respuestas crudas ni citas)."""
    return {
        "criterios": [
            {
                "criterio_id": c.criterio_id,
                "nivel_elegido": c.nivel_elegido,
                "justificacion": c.justificacion,
                "fortalezas": c.fortalezas,
                "debilidades": c.debilidades,
                "recomendacion": c.recomendacion,
            }
            for c in resultado.criterios
        ],
        "aprendizajes_identificados": resultado.aprendizajes_identificados,
        "como_aplico_conocimientos": resultado.como_aplico_conocimientos,
        "aspectos_a_fortalecer": resultado.aspectos_a_fortalecer,
        "retroalimentacion_general": resultado.retroalimentacion_general,
    }


def _guardar_exito(
    db: Session,
    evaluacion: Evaluacion,
    version: RubricaVersion,
    resultado: ResultadoIA,
    usuario_id: uuid.UUID | None,
) -> None:
    """Calcula la nota con nota.py y guarda criterios, resultado y auditoría."""
    criterios = version.contenido["criterios"]
    elegidos = _validar_resultado(criterios, resultado)
    nota = calcular_nota(criterios, elegidos)
    por_id = {c.criterio_id: c for c in resultado.criterios}
    for criterio in criterios:
        item = por_id[criterio["id"]]
        db.add(
            EvaluacionCriterio(
                evaluacion_id=evaluacion.id,
                criterio_id=item.criterio_id,
                nivel_ia=item.nivel_elegido,
                nivel_final=item.nivel_elegido,
                puntaje_normalizado=nota.normalizados[item.criterio_id],
                evidencias=item.evidencias,
                evidencias_verificadas=item.citas,
                justificacion=item.justificacion,
            )
        )
    evaluacion.nota = nota.nota
    evaluacion.estado = "borrador"
    evaluacion.prompt_version = resultado.version_prompt
    evaluacion.resultado = _resultado_json(resultado)
    evaluacion.error = None
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            entidad="evaluaciones",
            entidad_id=str(evaluacion.id),
            accion="evaluacion_ia",
            despues={
                "respuestas_crudas": resultado.respuestas_crudas,
                "version_prompt": resultado.version_prompt,
            },
        )
    )


def _solicitud(
    db: Session, evaluacion: Evaluacion, entrega: Entrega, cargar_material: CargadorMaterial
) -> tuple[RubricaVersion, SolicitudEvaluacion]:
    """Arma la solicitud con la versión de rúbrica DE LA ENTREGA y el material saneado."""
    version = db.get(RubricaVersion, entrega.rubrica_version_id)
    laboratorio = db.get(Laboratorio, entrega.laboratorio_id)
    if version is None or laboratorio is None:
        raise ResultadoIncoherenteError("Falta la versión de rúbrica o el laboratorio.")
    material = cargar_material(db, entrega)
    if not material.texto_informe.strip():
        raise DominioError(MSG_SIN_TEXTO)
    return version, SolicitudEvaluacion(
        rubrica=version.contenido,
        descripcion=laboratorio.descripcion or "",
        objetivos=laboratorio.objetivos or "",
        texto_informe=material.texto_informe,
        resumen_codigo=material.resumen_codigo,
        resultados_verificacion=sanear_verificacion(material.resultados_verificacion),
        proveedor=evaluacion.proveedor or "",
        modelo=evaluacion.modelo or "",
        temperatura=evaluacion.temperatura or 0.0,
    )


def _evaluar(
    db: Session,
    evaluacion_id: int,
    usuario_id: uuid.UUID | None,
    evaluador: Evaluador,
    cargar_material: CargadorMaterial,
) -> None:
    """Ejecuta la evaluación y confirma el resultado (lanza excepción si algo falla)."""
    evaluacion = db.get(Evaluacion, evaluacion_id)
    if evaluacion is None or evaluacion.estado != "procesando":
        return
    entrega = db.get(Entrega, evaluacion.entrega_id)
    if entrega is None:
        raise ResultadoIncoherenteError("La entrega de la evaluación ya no existe.")
    version, solicitud = _solicitud(db, evaluacion, entrega, cargar_material)
    resultado = evaluador(solicitud)
    _guardar_exito(db, evaluacion, version, resultado, usuario_id)
    db.commit()


def _detalle_error(error: Exception) -> dict[str, Any]:
    """Detalle técnico del fallo (solo para auditoría)."""
    detalle: dict[str, Any] = {
        "tipo": type(error).__name__,
        "mensaje": str(error)[:LIMITE_MENSAJE_AUDITORIA],
        "errores": [str(e) for e in getattr(error, "errores", [])],
        "respuestas_crudas": [str(c) for c in getattr(error, "respuestas_crudas", [])],
    }
    if error.__cause__ is not None:
        detalle["causa"] = repr(error.__cause__)[:LIMITE_MENSAJE_AUDITORIA]
    return detalle


def _registrar_error(
    fabrica: Callable[[], Session],
    evaluacion_id: int,
    usuario_id: uuid.UUID | None,
    error: Exception,
) -> None:
    """Deja la evaluación en `error` con mensaje genérico; el detalle va a auditoría."""
    try:
        with fabrica() as db:
            evaluacion = db.get(Evaluacion, evaluacion_id)
            if evaluacion is None:
                return
            evaluacion.estado = "error"
            evaluacion.error = MSG_ERROR_GENERICO
            evaluacion.nota = None
            db.add(
                Auditoria(
                    usuario_id=usuario_id,
                    entidad="evaluaciones",
                    entidad_id=str(evaluacion_id),
                    accion="evaluacion_ia_error",
                    despues=_detalle_error(error),
                )
            )
            db.commit()
    except Exception as segundo:  # la tarea de fondo nunca debe relanzar
        logger.error(
            "No se pudo registrar el error de la evaluación %s (%s).",
            evaluacion_id,
            type(segundo).__name__,
        )


def ejecutar_evaluacion(
    evaluacion_id: int,
    usuario_id: uuid.UUID | None,
    fabrica: Callable[[], Session],
    evaluador: Evaluador,
    cargar_material: CargadorMaterial,
) -> None:
    """Tarea de fondo: evalúa con su propia sesión; nunca relanza ni deja `procesando`."""
    try:
        with fabrica() as db:
            try:
                _evaluar(db, evaluacion_id, usuario_id, evaluador, cargar_material)
            except Exception:
                db.rollback()
                raise
    except Exception as error:  # cualquier fallo termina en estado `error`
        logger.warning(
            "La evaluación %s terminó en error (%s).", evaluacion_id, type(error).__name__
        )
        _registrar_error(fabrica, evaluacion_id, usuario_id, error)


# ---------- Consulta ----------


def obtener_detalle(db: Session, evaluacion_id: int, perfil: Perfil) -> DetalleEvaluacion:
    """Detalle según rol: docente/admin todo; estudiante solo lo propio y `publicada`."""
    evaluacion = db.get(Evaluacion, evaluacion_id)
    if evaluacion is None:
        raise NoEncontradoError(MSG_EVALUACION_NO_EXISTE)
    entrega = db.get(Entrega, evaluacion.entrega_id)
    es_docente = _es_docente(perfil)
    if entrega is None or not (es_docente or entrega.estudiante_id == perfil.id):
        raise NoEncontradoError(MSG_EVALUACION_NO_EXISTE)
    if not es_docente and evaluacion.estado != "publicada":
        raise PendienteRevisionError(MSG_PENDIENTE)
    criterios = list(
        db.scalars(
            select(EvaluacionCriterio)
            .where(EvaluacionCriterio.evaluacion_id == evaluacion.id)
            .order_by(EvaluacionCriterio.id)
        )
    )
    version = db.get(RubricaVersion, entrega.rubrica_version_id)
    return DetalleEvaluacion(evaluacion, criterios, version, vista_estudiante=not es_docente)

