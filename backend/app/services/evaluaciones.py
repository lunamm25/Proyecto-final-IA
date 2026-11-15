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
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import (
    Auditoria,
    ConfigIA,
    Entrega,
    Evaluacion,
    EvaluacionCriterio,
    Laboratorio,
    Perfil,
    RubricaVersion,
    VerificacionCodigo,
)
from app.models.tipos import ESTADOS_EVALUACION
from app.services.errores import (
    ConflictoError,
    DatosInvalidosError,
    DominioError,
    NoEncontradoError,
    ProhibidoError,
)
from app.services.evaluador_ia import Evaluador, ResultadoIA, SolicitudEvaluacion
from app.services.fechas import a_utc
from app.services.material import CargadorMaterial, resumen_verificacion, sanear_verificacion
from app.services.nota import calcular_nota
from app.services.rubricas import validar_rubrica
from app.services.secretos import detalle_error_tachado

logger = logging.getLogger(__name__)

TEMPERATURA_MAXIMA = 0.2
LIMITE_MENSAJE_AUDITORIA = 4_000
# Minutos tras los que una evaluación en `procesando` se da por atascada y pasa a `error` al
# relanzar. Peor caso normal de la IA: ~3 intentos × 120 s + carga del material (RNF-04 pide
# < 2 min), así que 10 min deja margen de sobra. Cambia este número si hace falta.
MINUTOS_MAX_PROCESANDO = 10
ESTADOS_QUE_BLOQUEAN_AL_ESTUDIANTE = ("borrador", "en_revision", "aprobada", "publicada")

MSG_ENTREGA_NO_EXISTE = "La entrega no existe."
MSG_EVALUACION_NO_EXISTE = "La evaluación no existe."
MSG_EN_CURSO = "Ya hay una evaluación en curso para esta entrega."
MSG_YA_EVALUADA = "Esta entrega ya tiene una evaluación en estado '{}'; no puedes lanzar otra."
MSG_SIN_VERSION = "La entrega no tiene una versión de rúbrica aprobada; no se puede evaluar."
MSG_RUBRICA_INCONSISTENTE = (
    "La versión de la rúbrica de esta entrega tiene inconsistencias; no se puede evaluar: {}"
)
MSG_RUBRICA_NO_LISTA = "La rúbrica de este laboratorio no está lista. Avisa a tu docente."
MSG_PENDIENTE = "La evaluación está pendiente de revisión docente."
MSG_ERROR_GENERICO = (
    "No se pudo completar la evaluación automática. Intenta de nuevo o contacta al docente."
)
MSG_SIN_TEXTO = "La entrega no tiene texto de informe ni código legible para evaluar."
TIPO_SANDBOX = "subprocess"
MSG_ESTADO_INVALIDO = "El estado '{}' no es válido. Valores permitidos: {}."


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
    entrega: Entrega | None = None
    estudiante: Perfil | None = None
    verificacion: dict[str, Any] | None = None


@dataclass(frozen=True)
class FilaListado:
    """Evaluación del listado docente con su entrega, estudiante y laboratorio."""

    evaluacion: Evaluacion
    entrega: Entrega
    estudiante: Perfil
    laboratorio: Laboratorio


@dataclass(frozen=True)
class PaginaEvaluaciones:
    """Una página del listado y el total de evaluaciones que cumplen los filtros."""

    filas: list[FilaListado]
    total: int


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


def _version_evaluable(db: Session, entrega: Entrega, perfil: Perfil) -> RubricaVersion:
    """Versión aprobada y sin inconsistencias (o 409; el estudiante no ve la lista)."""
    version = db.get(RubricaVersion, entrega.rubrica_version_id)
    if version is None or version.estado != "aprobada":
        raise ConflictoError(MSG_SIN_VERSION)
    inconsistencias = validar_rubrica(version.contenido)
    if inconsistencias and not _es_docente(perfil):
        raise ConflictoError(MSG_RUBRICA_NO_LISTA)
    if inconsistencias:
        raise ConflictoError(MSG_RUBRICA_INCONSISTENTE.format(" ".join(inconsistencias)))
    return version


def _hay_evaluacion_en_curso(db: Session, entrega_id: int) -> bool:
    """True si la entrega ya tiene una evaluación en `procesando`."""
    consulta = select(Evaluacion.id).where(
        Evaluacion.entrega_id == entrega_id, Evaluacion.estado == "procesando"
    )
    return db.scalar(consulta.limit(1)) is not None


def esta_atascada(creada_en: datetime | None, ahora: datetime) -> bool:
    """True si lleva más de MINUTOS_MAX_PROCESANDO (fechas con o sin zona se tratan en UTC)."""
    creada = a_utc(creada_en)
    if creada is None:
        return False
    return a_utc(ahora) - creada > timedelta(minutes=MINUTOS_MAX_PROCESANDO)


def _auditar_tiempo_agotado(db: Session, evaluacion: Evaluacion) -> None:
    """Auditoría del sistema (sin usuario) de una evaluación atascada que pasa a `error`."""
    db.add(
        Auditoria(
            usuario_id=None,
            entidad="evaluaciones",
            entidad_id=str(evaluacion.id),
            accion="evaluacion_ia_error",
            despues={"tipo": "TiempoAgotado", "minutos": MINUTOS_MAX_PROCESANDO},
        )
    )


def recuperar_atascadas(db: Session, entrega_id: int, ahora: datetime | None = None) -> int:
    """Pasa a `error` las evaluaciones atascadas de la entrega y lo audita (un solo commit).

    Si la escritura falla se deshace todo (nada queda a medias) y se sigue: la evaluación
    atascada sigue en `procesando` y el lanzamiento responderá 409.
    """
    ahora = ahora or datetime.now(UTC)
    consulta = (
        select(Evaluacion)
        .where(Evaluacion.entrega_id == entrega_id, Evaluacion.estado == "procesando")
        .with_for_update()
    )
    atascadas = [e for e in db.scalars(consulta) if esta_atascada(e.creada_en, ahora)]
    if not atascadas:
        return 0
    for evaluacion in atascadas:
        evaluacion.estado = "error"
        evaluacion.error = MSG_ERROR_GENERICO
        evaluacion.nota = None
        _auditar_tiempo_agotado(db, evaluacion)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(
            "No se pudieron recuperar las evaluaciones atascadas de la entrega %s (%s).",
            entrega_id,
            type(error).__name__,
        )
        return 0
    logger.warning(
        "Evaluaciones atascadas de la entrega %s pasadas a error: %s.", entrega_id, len(atascadas)
    )
    return len(atascadas)


def _estado_que_bloquea(db: Session, entrega_id: int) -> str | None:
    """Estado de la evaluación más reciente que impide relanzar al estudiante (o None)."""
    consulta = (
        select(Evaluacion.estado)
        .where(
            Evaluacion.entrega_id == entrega_id,
            Evaluacion.estado.in_(ESTADOS_QUE_BLOQUEAN_AL_ESTUDIANTE),
        )
        .order_by(Evaluacion.creada_en.desc(), Evaluacion.id.desc())
        .limit(1)
    )
    return db.scalar(consulta)


def _comprobar_relanzamiento(db: Session, entrega_id: int, perfil: Perfil) -> None:
    """409 si hay una en curso (todos) o, para el estudiante, una activa o publicada."""
    if _hay_evaluacion_en_curso(db, entrega_id):
        raise ConflictoError(MSG_EN_CURSO)
    if _es_docente(perfil):
        return
    estado = _estado_que_bloquea(db, entrega_id)
    if estado is not None:
        raise ConflictoError(MSG_YA_EVALUADA.format(estado))


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


def _auditar_lanzamiento(db: Session, evaluacion: Evaluacion, perfil: Perfil) -> None:
    """Registra en auditoría quién lanzó la evaluación y con qué configuración de IA."""
    db.add(
        Auditoria(
            usuario_id=perfil.id,
            entidad="evaluaciones",
            entidad_id=str(evaluacion.id),
            accion="lanzar_evaluacion",
            despues={
                "estado": evaluacion.estado,
                "entrega_id": evaluacion.entrega_id,
                "proveedor": evaluacion.proveedor,
                "modelo": evaluacion.modelo,
                "temperatura": evaluacion.temperatura,
            },
        )
    )


def lanzar_evaluacion(
    db: Session, entrega_id: int, perfil: Perfil, settings: Settings
) -> Evaluacion:
    """Valida permisos y rúbrica, recupera atascadas y crea la evaluación en `procesando`.

    La recuperación de atascadas se confirma antes (su propio commit) para que no se pierda si
    el lanzamiento termina en 409; el lanzamiento y su auditoría van en otro commit.
    """
    entrega = _entrega_visible(db, entrega_id, perfil)
    _version_evaluable(db, entrega, perfil)
    recuperar_atascadas(db, entrega.id)
    _comprobar_relanzamiento(db, entrega.id, perfil)
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
        db.flush()
        _auditar_lanzamiento(db, evaluacion, perfil)
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
    verificacion: dict[str, Any] | None = None,
) -> None:
    """Calcula la nota con nota.py y guarda criterios, resultado, verificación y auditoría.

    Si la evaluación ya no está en `procesando` (p. ej. se dio por atascada), no escribe nada
    del resultado: solo deja constancia en auditoría de que se descartó.
    """
    if not _sigue_procesando(db, evaluacion.id):
        crudas = {
            "version_prompt": resultado.version_prompt,
            "respuestas_crudas": resultado.respuestas_crudas,
        }
        _auditar_descarte(db, evaluacion.id, usuario_id, crudas)
        return
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
    if verificacion is not None:
        db.add(
            VerificacionCodigo(
                evaluacion_id=evaluacion.id, metricas=verificacion, sandbox=TIPO_SANDBOX
            )
        )
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


def _sigue_procesando(db: Session, evaluacion_id: int) -> bool:
    """Recarga la evaluación bloqueándola y dice si sigue en `procesando`."""
    evaluacion = db.get(Evaluacion, evaluacion_id, with_for_update=True, populate_existing=True)
    return evaluacion is not None and evaluacion.estado == "procesando"


def _auditar_descarte(
    db: Session, evaluacion_id: int, usuario_id: uuid.UUID | None, despues: dict[str, Any]
) -> None:
    """Registra que el resultado tardío de la tarea se descartó (el estado no cambia)."""
    logger.warning(
        "Resultado tardío de la evaluación %s descartado: ya no estaba en procesando.",
        evaluacion_id,
    )
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            entidad="evaluaciones",
            entidad_id=str(evaluacion_id),
            accion="evaluacion_ia_descartada",
            despues={"motivo": "La evaluación ya no estaba en procesando.", **despues},
        )
    )


def _solicitud(
    db: Session, evaluacion: Evaluacion, entrega: Entrega, cargar_material: CargadorMaterial
) -> tuple[RubricaVersion, SolicitudEvaluacion, dict[str, Any] | None]:
    """Solicitud con la versión de rúbrica DE LA ENTREGA, el material saneado y la verificación."""
    version = db.get(RubricaVersion, entrega.rubrica_version_id)
    laboratorio = db.get(Laboratorio, entrega.laboratorio_id)
    if version is None or laboratorio is None:
        raise ResultadoIncoherenteError("Falta la versión de rúbrica o el laboratorio.")
    material = cargar_material(db, entrega)
    if not material.texto_informe.strip() and not (material.resumen_codigo or "").strip():
        raise DominioError(MSG_SIN_TEXTO)
    verificacion = resumen_verificacion(material.resultados_verificacion)
    solicitud = SolicitudEvaluacion(
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
    return version, solicitud, verificacion


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
    version, solicitud, verificacion = _solicitud(db, evaluacion, entrega, cargar_material)
    resultado = evaluador(solicitud)
    _guardar_exito(db, evaluacion, version, resultado, usuario_id, verificacion)
    db.commit()


def _detalle_error(error: Exception, settings: Settings) -> dict[str, Any]:
    """Detalle técnico del fallo, con secretos tachados (solo para auditoría)."""
    return detalle_error_tachado(error, settings, LIMITE_MENSAJE_AUDITORIA)


def _registrar_error(
    fabrica: Callable[[], Session],
    evaluacion_id: int,
    usuario_id: uuid.UUID | None,
    error: Exception,
    settings: Settings | None = None,
) -> None:
    """Deja la evaluación en `error` con mensaje genérico; el detalle tachado va a auditoría."""
    try:
        with fabrica() as db:
            evaluacion = db.get(Evaluacion, evaluacion_id)
            if evaluacion is None:
                return
            if not _sigue_procesando(db, evaluacion_id):
                detalle = _detalle_error(error, settings or get_settings())
                _auditar_descarte(db, evaluacion_id, usuario_id, {"error": detalle})
                db.commit()
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
                    despues=_detalle_error(error, settings or get_settings()),
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
    settings: Settings | None = None,
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
        _registrar_error(fabrica, evaluacion_id, usuario_id, error, settings)


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
    estudiante = db.get(Perfil, entrega.estudiante_id)
    return DetalleEvaluacion(
        evaluacion,
        criterios,
        version,
        vista_estudiante=not es_docente,
        entrega=entrega,
        estudiante=estudiante,
        verificacion=verificacion_resumida(db, evaluacion.id) if es_docente else None,
    )


def verificacion_resumida(db: Session, evaluacion_id: int) -> dict[str, Any] | None:
    """Los 3 campos guardados de la ejecución en sandbox (o None si no se ejecutó)."""
    fila = db.scalar(
        select(VerificacionCodigo).where(VerificacionCodigo.evaluacion_id == evaluacion_id)
    )
    return resumen_verificacion(fila.metricas) if fila else None


def listar_evaluaciones(
    db: Session,
    *,
    laboratorio_id: int | None,
    estado: str | None,
    estudiante_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> PaginaEvaluaciones:
    """Listado docente con filtros opcionales, de la más reciente a la más antigua."""
    if estado is not None and estado not in ESTADOS_EVALUACION:
        raise DatosInvalidosError(MSG_ESTADO_INVALIDO.format(estado, ", ".join(ESTADOS_EVALUACION)))
    filtros = []
    if laboratorio_id is not None:
        filtros.append(Entrega.laboratorio_id == laboratorio_id)
    if estado is not None:
        filtros.append(Evaluacion.estado == estado)
    if estudiante_id is not None:
        filtros.append(Entrega.estudiante_id == estudiante_id)
    total = db.scalar(
        select(func.count(Evaluacion.id))
        .join(Entrega, Evaluacion.entrega_id == Entrega.id)
        .where(*filtros)
    )
    consulta = (
        select(Evaluacion, Entrega, Perfil, Laboratorio)
        .join(Entrega, Evaluacion.entrega_id == Entrega.id)
        .join(Perfil, Entrega.estudiante_id == Perfil.id)
        .join(Laboratorio, Entrega.laboratorio_id == Laboratorio.id)
        .where(*filtros)
        .order_by(Evaluacion.creada_en.desc(), Evaluacion.id.desc())
        .limit(limit)
        .offset(offset)
    )
    filas = [FilaListado(*fila) for fila in db.execute(consulta).all()]
    return PaginaEvaluaciones(filas, total or 0)
