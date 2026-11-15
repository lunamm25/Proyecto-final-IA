"""Trazabilidad de una evaluación (RF-07 CA4, CLAUDE.md §5): eventos de auditoría en orden.

Solo para docente/admin. Incluye las respuestas crudas guardadas en auditoría, pero nunca claves
ni datos de conexión: se eliminan las claves de diccionario que parezcan secretos y, como segunda
capa, se tachan las credenciales que aparezcan dentro de los textos (sin recortarlos).
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import Auditoria, Entrega, Evaluacion, Perfil, RubricaVersion
from app.services.errores import NoEncontradoError
from app.services.evaluaciones import MSG_EVALUACION_NO_EXISTE, verificacion_resumida
from app.services.secretos import tachar_credenciales

PATRONES_SECRETOS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "contrasena",
    "contraseña",
    "database_url",
    "authorization",
    "credential",
)


@dataclass(frozen=True)
class EventoTraza:
    """Un registro de auditoría con su usuario (None si lo hizo el sistema)."""

    auditoria: Auditoria
    usuario: Perfil | None


@dataclass(frozen=True)
class Traza:
    """Evaluación, su versión de rúbrica y sus eventos en orden cronológico."""

    evaluacion: Evaluacion
    rubrica_version: RubricaVersion | None
    eventos: list[EventoTraza]
    verificacion: dict[str, Any] | None = None


def _parece_secreto(clave: str) -> bool:
    """True si el nombre de la clave sugiere un secreto (api_key, token, password, ...)."""
    nombre = clave.lower().replace("-", "_")
    return nombre == "key" or nombre.endswith("_key") or any(p in nombre for p in PATRONES_SECRETOS)


def _limpiar(valor: Any, settings: Settings) -> Any:
    """Quita las claves sensibles y tacha credenciales en los textos (recursivo)."""
    if isinstance(valor, dict):
        return {
            k: _limpiar(v, settings)
            for k, v in valor.items()
            if not (isinstance(k, str) and _parece_secreto(k))
        }
    if isinstance(valor, list):
        return [_limpiar(v, settings) for v in valor]
    if isinstance(valor, str):
        return tachar_credenciales(valor, settings)
    return valor


def sin_secretos(valor: Any, settings: Settings | None = None) -> Any:
    """Copia del valor JSON sin claves que parezcan secretos y con credenciales tachadas."""
    return _limpiar(valor, settings or get_settings())


def obtener_traza(db: Session, evaluacion_id: int) -> Traza:
    """Eventos de auditoría de la evaluación (por fecha y luego id) y su contexto."""
    evaluacion = db.get(Evaluacion, evaluacion_id)
    if evaluacion is None:
        raise NoEncontradoError(MSG_EVALUACION_NO_EXISTE)
    entrega = db.get(Entrega, evaluacion.entrega_id)
    version = db.get(RubricaVersion, entrega.rubrica_version_id) if entrega else None
    consulta = (
        select(Auditoria, Perfil)
        .outerjoin(Perfil, Auditoria.usuario_id == Perfil.id)
        .where(Auditoria.entidad == "evaluaciones", Auditoria.entidad_id == str(evaluacion.id))
        .order_by(Auditoria.creado_en, Auditoria.id)
    )
    eventos = [EventoTraza(fila, perfil) for fila, perfil in db.execute(consulta).all()]
    return Traza(evaluacion, version, eventos, verificacion_resumida(db, evaluacion.id))
