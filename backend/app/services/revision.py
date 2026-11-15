"""Revisión docente HITL (RF-07): transiciones, ajuste de niveles y edición de retroalimentación.

Cada acción carga la evaluación con bloqueo de fila (`with_for_update`: en Postgres impide que dos
docentes la cambien a la vez; SQLite lo ignora), aplica el cambio y su registro en `auditoria`, y
confirma todo en UN solo commit. Si algo falla se hace rollback: nunca queda un cambio sin su
registro ni un registro sin su cambio. La nota la recalcula siempre `nota.py`.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from functools import wraps
from typing import Any, Concatenate, ParamSpec, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Auditoria, Entrega, Evaluacion, EvaluacionCriterio, Perfil, RubricaVersion
from app.services.errores import ConflictoError, DatosInvalidosError, NoEncontradoError
from app.services.evaluaciones import MSG_EVALUACION_NO_EXISTE
from app.services.nota import calcular_nota
from app.services.rubricas import validar_rubrica

P = ParamSpec("P")
R = TypeVar("R")
Accion = Callable[Concatenate[Session, P], R]

ESTADOS_EDITABLES = ("borrador", "en_revision")
# Acción → (estado de origen permitido, estado de destino). Ninguna sale de `error`/`procesando`.
TRANSICIONES: dict[str, tuple[str, str]] = {
    "revisar": ("borrador", "en_revision"),
    "aprobar": ("en_revision", "aprobada"),
    "publicar": ("aprobada", "publicada"),
}
VERBOS = {"revisar": "pasar a revisión", "aprobar": "aprobar", "publicar": "publicar"}
ACCIONES_AUDITORIA = {"revisar": "pasar_a_revision", "aprobar": "aprobar", "publicar": "publicar"}

CAMPOS_GENERALES = (
    "retroalimentacion_general",
    "como_aplico_conocimientos",
    "aprendizajes_identificados",
    "aspectos_a_fortalecer",
)
CAMPOS_CRITERIO = ("justificacion", "fortalezas", "debilidades", "recomendacion")

MSG_TRANSICION = "No se puede {} una evaluación en estado '{}'."
MSG_NO_EDITABLE = (
    "No se puede {} una evaluación en estado '{}'. Solo se permite en 'borrador' o 'en_revision'."
)
MSG_CRITERIO_NO_EXISTE = "El criterio '{}' no existe en esta evaluación."
MSG_NIVEL_NO_EXISTE = "El nivel '{}' no existe en el criterio '{}'."
MSG_MOTIVO = "El motivo del ajuste es obligatorio."
MSG_SIN_VERSION = "La entrega de esta evaluación no tiene versión de rúbrica."
MSG_NO_RECALCULA = "No se puede recalcular la nota: {}"
MSG_RUBRICA_INVALIDA = "No se puede aprobar: la rúbrica de esta entrega tiene inconsistencias: {}"
MSG_FALTAN_NIVELES = "No se puede aprobar: falta el nivel final de los criterios {}."
MSG_SIN_EDICION = "Indica al menos un texto de retroalimentación para editar."
MSG_CRITERIO_SIN_TEXTO = "El criterio '{}' no indica ningún texto para editar."
MSG_CRITERIO_REPETIDO = "El criterio '{}' aparece más de una vez."


def _en_transaccion(funcion: Accion[P, R]) -> Accion[P, R]:
    """Confirma con un único commit si todo sale bien; si algo falla, rollback y relanza."""

    @wraps(funcion)
    def envoltura(db: Session, *args: P.args, **kwargs: P.kwargs) -> R:
        try:
            resultado = funcion(db, *args, **kwargs)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return resultado

    return envoltura


def _cargar(db: Session, evaluacion_id: int) -> Evaluacion:
    """Evaluación bloqueada para escritura (FOR UPDATE en Postgres) o 404."""
    consulta = select(Evaluacion).where(Evaluacion.id == evaluacion_id).with_for_update()
    evaluacion = db.scalar(consulta)
    if evaluacion is None:
        raise NoEncontradoError(MSG_EVALUACION_NO_EXISTE)
    return evaluacion


def _filas(db: Session, evaluacion_id: int) -> dict[str, EvaluacionCriterio]:
    """Criterios evaluados por criterio_id."""
    consulta = select(EvaluacionCriterio).where(EvaluacionCriterio.evaluacion_id == evaluacion_id)
    return {f.criterio_id: f for f in db.scalars(consulta.order_by(EvaluacionCriterio.id))}


def _version(db: Session, evaluacion: Evaluacion) -> RubricaVersion:
    """Versión de rúbrica DE LA ENTREGA (no la vigente del laboratorio)."""
    entrega = db.get(Entrega, evaluacion.entrega_id)
    version = db.get(RubricaVersion, entrega.rubrica_version_id) if entrega else None
    if version is None:
        raise ConflictoError(MSG_SIN_VERSION)
    return version


def _numero(nota: Decimal | None) -> float | None:
    """Nota como número JSON para la auditoría."""
    return float(nota) if nota is not None else None


def _auditar(
    db: Session,
    perfil: Perfil,
    evaluacion: Evaluacion,
    accion: str,
    antes: dict[str, Any],
    despues: dict[str, Any],
    motivo: str | None = None,
) -> None:
    """Agrega el registro de auditoría a la misma transacción que el cambio."""
    db.add(
        Auditoria(
            usuario_id=perfil.id,
            entidad="evaluaciones",
            entidad_id=str(evaluacion.id),
            accion=accion,
            antes=antes,
            despues=despues,
            motivo=motivo,
        )
    )


def _exigir_editable(evaluacion: Evaluacion, que: str) -> None:
    """Solo se ajusta o edita en `borrador` o `en_revision` (409 en otro caso)."""
    if evaluacion.estado not in ESTADOS_EDITABLES:
        raise ConflictoError(MSG_NO_EDITABLE.format(que, evaluacion.estado))


def _exigir_transicion(evaluacion: Evaluacion, accion: str) -> str:
    """Comprueba la tabla TRANSICIONES y devuelve el estado de destino (409 si no aplica)."""
    origen, destino = TRANSICIONES[accion]
    if evaluacion.estado != origen:
        raise ConflictoError(MSG_TRANSICION.format(VERBOS[accion], evaluacion.estado))
    return destino


def _recalcular(
    evaluacion: Evaluacion, filas: dict[str, EvaluacionCriterio], version: RubricaVersion
) -> Decimal:
    """Recalcula nota y normalizados con nota.py usando los niveles finales."""
    elegidos = {cid: fila.nivel_final for cid, fila in filas.items()}
    try:
        resultado = calcular_nota(version.contenido["criterios"], elegidos)
    except (ValueError, KeyError, TypeError) as error:
        raise ConflictoError(MSG_NO_RECALCULA.format(error)) from None
    evaluacion.nota = resultado.nota
    for cid, fila in filas.items():
        fila.puntaje_normalizado = resultado.normalizados[cid]
    return resultado.nota


# ---------- Transiciones de estado ----------


@_en_transaccion
def pasar_a_revision(db: Session, evaluacion_id: int, perfil: Perfil) -> None:
    """borrador → en_revision."""
    evaluacion = _cargar(db, evaluacion_id)
    antes = evaluacion.estado
    evaluacion.estado = _exigir_transicion(evaluacion, "revisar")
    _auditar(
        db, perfil, evaluacion, "pasar_a_revision", {"estado": antes}, {"estado": evaluacion.estado}
    )


def _niveles_faltantes(version: RubricaVersion, filas: dict[str, EvaluacionCriterio]) -> list[str]:
    """Criterios de la rúbrica sin fila o sin nivel final."""
    ids = [c.get("id") for c in version.contenido.get("criterios", [])]
    return [cid for cid in ids if cid not in filas or filas[cid].nivel_final is None]


@_en_transaccion
def aprobar(db: Session, evaluacion_id: int, perfil: Perfil) -> None:
    """en_revision → aprobada, con rúbrica válida, todos los niveles y nota confirmada."""
    evaluacion = _cargar(db, evaluacion_id)
    destino = _exigir_transicion(evaluacion, "aprobar")
    version = _version(db, evaluacion)
    inconsistencias = validar_rubrica(version.contenido)
    if inconsistencias:
        raise ConflictoError(MSG_RUBRICA_INVALIDA.format(" ".join(inconsistencias)))
    filas = _filas(db, evaluacion.id)
    faltantes = _niveles_faltantes(version, filas)
    if faltantes:
        raise ConflictoError(MSG_FALTAN_NIVELES.format(", ".join(map(str, faltantes))))
    antes = {"estado": evaluacion.estado, "nota": _numero(evaluacion.nota)}
    nota = _recalcular(evaluacion, filas, version)
    evaluacion.estado = destino
    evaluacion.aprobada_por = perfil.id
    evaluacion.aprobada_en = datetime.now(UTC)
    despues: dict[str, Any] = {
        "estado": destino,
        "nota": _numero(nota),
        "aprobada_en": evaluacion.aprobada_en.isoformat(),
    }
    if antes["nota"] != despues["nota"]:
        despues["nota_recalculada"] = True
    _auditar(db, perfil, evaluacion, "aprobar", antes, despues)


@_en_transaccion
def publicar(db: Session, evaluacion_id: int, perfil: Perfil) -> None:
    """aprobada → publicada: desde ahora la ve el estudiante."""
    evaluacion = _cargar(db, evaluacion_id)
    antes = evaluacion.estado
    evaluacion.estado = _exigir_transicion(evaluacion, "publicar")
    evaluacion.publicada_en = datetime.now(UTC)
    despues = {"estado": evaluacion.estado, "publicada_en": evaluacion.publicada_en.isoformat()}
    _auditar(db, perfil, evaluacion, "publicar", {"estado": antes}, despues)


# ---------- Ajuste de nivel ----------


def _validar_nivel(version: RubricaVersion, criterio_id: str, nivel: str) -> None:
    """El nivel debe existir en ESE criterio de la versión de la entrega (422)."""
    criterios = version.contenido.get("criterios", [])
    criterio = next((c for c in criterios if c.get("id") == criterio_id), None)
    nombres = {n.get("nombre") for n in criterio.get("niveles", [])} if criterio else set()
    if nivel not in nombres:
        raise DatosInvalidosError(MSG_NIVEL_NO_EXISTE.format(nivel, criterio_id))


@_en_transaccion
def ajustar_criterio(
    db: Session, evaluacion_id: int, criterio_id: str, nivel_final: str, motivo: str, perfil: Perfil
) -> None:
    """Cambia el nivel final (motivo obligatorio), recalcula la nota y lo audita."""
    evaluacion = _cargar(db, evaluacion_id)
    filas = _filas(db, evaluacion.id)
    fila = filas.get(criterio_id)
    if fila is None:
        raise NoEncontradoError(MSG_CRITERIO_NO_EXISTE.format(criterio_id))
    _exigir_editable(evaluacion, "ajustar el nivel de un criterio en")
    motivo = motivo.strip()
    if not motivo:
        raise DatosInvalidosError(MSG_MOTIVO)
    version = _version(db, evaluacion)
    _validar_nivel(version, criterio_id, nivel_final)
    if fila.nivel_final == nivel_final:
        return
    antes = {"criterio_id": criterio_id, "nivel_final": fila.nivel_final}
    antes["nota"] = _numero(evaluacion.nota)
    fila.nivel_final = nivel_final
    fila.ajuste_docente = motivo
    nota = _recalcular(evaluacion, filas, version)
    despues = {"criterio_id": criterio_id, "nivel_final": nivel_final, "nota": _numero(nota)}
    _auditar(db, perfil, evaluacion, "ajustar_criterio", antes, despues, motivo)


# ---------- Retroalimentación (original de la IA + edición del docente) ----------


def retro_general_ia(evaluacion: Evaluacion) -> dict[str, Any]:
    """Textos generales tal como los dejó la IA (`resultado`)."""
    resultado = evaluacion.resultado or {}
    return {campo: resultado[campo] for campo in CAMPOS_GENERALES if campo in resultado}


def retro_general_final(evaluacion: Evaluacion) -> dict[str, Any]:
    """Textos generales que se muestran: la edición del docente sobre el original."""
    return {**retro_general_ia(evaluacion), **(evaluacion.retroalimentacion_docente or {})}


def retro_criterio_ia(fila: EvaluacionCriterio, evaluacion: Evaluacion) -> dict[str, Any]:
    """Justificación, fortalezas, debilidades y recomendación de la IA para un criterio."""
    extras = (evaluacion.resultado or {}).get("criterios", [])
    extra = next((c for c in extras if c.get("criterio_id") == fila.criterio_id), {})
    return {
        "justificacion": fila.justificacion,
        "fortalezas": extra.get("fortalezas", []),
        "debilidades": extra.get("debilidades", []),
        "recomendacion": extra.get("recomendacion"),
    }


def retro_criterio_final(fila: EvaluacionCriterio, evaluacion: Evaluacion) -> dict[str, Any]:
    """Textos del criterio que se muestran: la edición del docente sobre el original."""
    return {**retro_criterio_ia(fila, evaluacion), **(fila.retroalimentacion_docente or {})}


def _aplicar(
    original: dict[str, Any], edicion: dict[str, Any] | None, cambios: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    """Aplica los cambios (None = volver al original) y devuelve (edición, antes, después)."""
    nueva = dict(edicion or {})
    antes: dict[str, Any] = {}
    despues: dict[str, Any] = {}
    for campo, valor in cambios.items():
        previo = nueva.get(campo, original.get(campo))
        if valor is None or valor == original.get(campo):
            nueva.pop(campo, None)
        else:
            nueva[campo] = valor
        actual = nueva.get(campo, original.get(campo))
        if actual != previo:
            antes[campo], despues[campo] = previo, actual
    return nueva or None, antes, despues


def _validar_edicion(general: dict[str, Any], criterios: list[dict[str, Any]]) -> None:
    """Debe haber algo que editar y cada criterio aparece una sola vez (422)."""
    if not general and not criterios:
        raise DatosInvalidosError(MSG_SIN_EDICION)
    vistos: set[str] = set()
    for item in criterios:
        cid = item["criterio_id"]
        if cid in vistos:
            raise DatosInvalidosError(MSG_CRITERIO_REPETIDO.format(cid))
        vistos.add(cid)
        if not any(campo in item for campo in CAMPOS_CRITERIO):
            raise DatosInvalidosError(MSG_CRITERIO_SIN_TEXTO.format(cid))


@_en_transaccion
def editar_retroalimentacion(
    db: Session,
    evaluacion_id: int,
    general: dict[str, Any],
    criterios: list[dict[str, Any]],
    motivo: str | None,
    perfil: Perfil,
) -> None:
    """Guarda la edición del docente sin tocar el texto de la IA y la audita."""
    evaluacion = _cargar(db, evaluacion_id)
    _validar_edicion(general, criterios)
    _exigir_editable(evaluacion, "editar la retroalimentación de")
    filas = _filas(db, evaluacion.id)
    faltante = next((c["criterio_id"] for c in criterios if c["criterio_id"] not in filas), None)
    if faltante is not None:
        raise NoEncontradoError(MSG_CRITERIO_NO_EXISTE.format(faltante))
    edicion, antes_g, despues_g = _aplicar(
        retro_general_ia(evaluacion), evaluacion.retroalimentacion_docente, general
    )
    evaluacion.retroalimentacion_docente = edicion
    antes: dict[str, Any] = {"general": antes_g, "criterios": {}}
    despues: dict[str, Any] = {"general": despues_g, "criterios": {}}
    for item in criterios:
        fila = filas[item["criterio_id"]]
        cambios = {c: item[c] for c in CAMPOS_CRITERIO if c in item}
        edicion_c, antes_c, despues_c = _aplicar(
            retro_criterio_ia(fila, evaluacion), fila.retroalimentacion_docente, cambios
        )
        fila.retroalimentacion_docente = edicion_c
        if despues_c:
            antes["criterios"][fila.criterio_id] = antes_c
            despues["criterios"][fila.criterio_id] = despues_c
    if despues_g or despues["criterios"]:
        motivo = (motivo or "").strip() or None
        _auditar(db, perfil, evaluacion, "editar_retroalimentacion", antes, despues, motivo)
