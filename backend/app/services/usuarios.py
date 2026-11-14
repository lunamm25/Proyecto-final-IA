"""Gestión de usuarios y roles (RF-01 CA3) con registro en auditoría."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Auditoria, Perfil
from app.models.tipos import ROLES
from app.services.errores import ConflictoError, DatosInvalidosError, NoEncontradoError

MSG_ROL_NO_VALIDO = "Rol no válido. Usa: estudiante, docente o admin."
MSG_USUARIO_NO_EXISTE = "El usuario no existe."
MSG_AUTO_DEGRADAR = (
    "No puedes quitarte tu propio rol de administrador. Pide a otro administrador que lo haga."
)
MSG_ULTIMO_ADMIN = "No se puede cambiar el rol: el sistema debe tener al menos un administrador."


def listar_usuarios(db: Session) -> list[Perfil]:
    """Perfiles ordenados por nombre (sin distinguir mayúsculas; sin nombre al final)."""
    consulta = select(Perfil).order_by(
        Perfil.nombre.is_(None), func.lower(Perfil.nombre), Perfil.id
    )
    return list(db.scalars(consulta))


def contar_admins(db: Session) -> int:
    """Número de perfiles con rol admin (bloquea esas filas en Postgres hasta el commit)."""
    ids = db.scalars(select(Perfil.id).where(Perfil.rol == "admin").with_for_update())
    return len(list(ids))


def _validar_rol(rol: str) -> str:
    """Devuelve el rol si es uno de los permitidos; si no, DatosInvalidosError."""
    if rol not in ROLES:
        raise DatosInvalidosError(MSG_ROL_NO_VALIDO)
    return rol


def _limpiar_motivo(motivo: str | None) -> str | None:
    """Quita espacios del motivo; vacío equivale a no enviarlo."""
    motivo = (motivo or "").strip()
    return motivo or None


def cambiar_rol(
    db: Session, actor: Perfil, usuario_id: uuid.UUID, rol: str, motivo: str | None
) -> Perfil:
    """Cambia el rol de un usuario y lo registra en auditoría en la misma transacción."""
    nuevo = _validar_rol(rol)
    usuario = db.get(Perfil, usuario_id)
    if usuario is None:
        raise NoEncontradoError(MSG_USUARIO_NO_EXISTE)
    anterior = usuario.rol
    if nuevo == anterior:
        return usuario
    if anterior == "admin":
        if usuario.id == actor.id:
            raise ConflictoError(MSG_AUTO_DEGRADAR)
        if contar_admins(db) <= 1:
            raise ConflictoError(MSG_ULTIMO_ADMIN)
    usuario.rol = nuevo
    db.add(
        Auditoria(
            usuario_id=actor.id,
            entidad="perfiles",
            entidad_id=str(usuario.id),
            accion="cambiar_rol",
            antes={"rol": anterior},
            despues={"rol": nuevo},
            motivo=_limpiar_motivo(motivo),
        )
    )
    db.commit()
    db.refresh(usuario)
    return usuario
