"""Cohortes y laboratorios: consulta y CRUD (RF-02 CA1).

Crear, editar y borrar quedan en `auditoria` en la MISMA transacción que el cambio: si la
auditoría no se puede escribir, se hace rollback y el cambio no se guarda.
"""

from dataclasses import dataclass

from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Auditoria, Cohorte, Entrega, Laboratorio, Perfil, Rubrica, RubricaVersion
from app.services.errores import ConflictoError, DatosInvalidosError, NoEncontradoError

MSG_LAB_NO_EXISTE = "El laboratorio no existe."
MSG_CON_ENTREGAS = "No se puede borrar: el laboratorio tiene entregas"
ENTIDAD_AUDITORIA = "laboratorios"
CAMPOS = ("cohorte_id", "codigo", "titulo", "descripcion", "objetivos")


@dataclass(frozen=True)
class DatosLaboratorio:
    """Campos editables de un laboratorio."""

    cohorte_id: int
    codigo: str
    titulo: str
    descripcion: str | None = None
    objetivos: str | None = None


def versiones_vigentes(db: Session) -> dict[int, int]:
    """Número de la versión aprobada más alta de cada laboratorio que tiene rúbrica."""
    filas = db.execute(
        select(Rubrica.laboratorio_id, func.max(RubricaVersion.version))
        .join(RubricaVersion, RubricaVersion.rubrica_id == Rubrica.id)
        .where(RubricaVersion.estado == "aprobada")
        .group_by(Rubrica.laboratorio_id)
    ).all()
    return {laboratorio_id: version for laboratorio_id, version in filas}


def listar_cohortes(db: Session) -> list[Cohorte]:
    """Cohortes ordenadas por número, con sus laboratorios ordenados por código."""
    consulta = select(Cohorte).options(selectinload(Cohorte.laboratorios)).order_by(Cohorte.numero)
    return list(db.scalars(consulta))


def _limpiar(datos: DatosLaboratorio) -> DatosLaboratorio:
    """Quita espacios y exige código y título no vacíos."""
    codigo, titulo = datos.codigo.strip(), datos.titulo.strip()
    if not codigo:
        raise DatosInvalidosError("El código del laboratorio no puede estar vacío.")
    if not titulo:
        raise DatosInvalidosError("El título del laboratorio no puede estar vacío.")
    return DatosLaboratorio(datos.cohorte_id, codigo, titulo, datos.descripcion, datos.objetivos)


def _validar(db: Session, datos: DatosLaboratorio, excluir_id: int | None = None) -> None:
    """Comprueba que la cohorte exista y que el código no lo use otro laboratorio."""
    if db.get(Cohorte, datos.cohorte_id) is None:
        raise DatosInvalidosError(f"La cohorte {datos.cohorte_id} no existe.")
    consulta = select(Laboratorio.id).where(Laboratorio.codigo == datos.codigo)
    if excluir_id is not None:
        consulta = consulta.where(Laboratorio.id != excluir_id)
    if db.scalar(consulta) is not None:
        raise ConflictoError(f"Ya existe un laboratorio con el código {datos.codigo}")


def _campos(laboratorio: Laboratorio) -> dict[str, object]:
    """Campos editables del laboratorio (para auditoría)."""
    return {campo: getattr(laboratorio, campo) for campo in CAMPOS}


def _auditar(
    db: Session,
    actor: Perfil,
    laboratorio_id: int,
    accion: str,
    antes: dict[str, object] | None = None,
    despues: dict[str, object] | None = None,
) -> None:
    """Añade la auditoría del cambio (se confirma junto con él)."""
    db.add(
        Auditoria(
            usuario_id=actor.id,
            entidad=ENTIDAD_AUDITORIA,
            entidad_id=str(laboratorio_id),
            accion=accion,
            antes=antes,
            despues=despues,
        )
    )


def _confirmar(db: Session, laboratorio: Laboratorio) -> Laboratorio:
    """Hace commit (rollback si falla) traduciendo choques de unicidad a 409."""
    codigo = laboratorio.codigo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictoError(f"Ya existe un laboratorio con el código {codigo}") from None
    except Exception:
        db.rollback()
        raise
    db.refresh(laboratorio)
    return laboratorio


def obtener_laboratorio(db: Session, laboratorio_id: int) -> Laboratorio:
    """Devuelve el laboratorio o lanza NoEncontradoError."""
    laboratorio = db.get(Laboratorio, laboratorio_id)
    if laboratorio is None:
        raise NoEncontradoError(MSG_LAB_NO_EXISTE)
    return laboratorio


def crear_laboratorio(db: Session, datos: DatosLaboratorio, actor: Perfil) -> Laboratorio:
    """Crea un laboratorio validando cohorte y código único, y lo audita."""
    datos = _limpiar(datos)
    _validar(db, datos)
    laboratorio = Laboratorio(**datos.__dict__)
    db.add(laboratorio)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictoError(f"Ya existe un laboratorio con el código {datos.codigo}") from None
    _auditar(db, actor, laboratorio.id, "crear_laboratorio", despues=_campos(laboratorio))
    return _confirmar(db, laboratorio)


def actualizar_laboratorio(
    db: Session, laboratorio_id: int, datos: DatosLaboratorio, actor: Perfil
) -> Laboratorio:
    """Reemplaza los campos de un laboratorio; audita solo lo que cambia (nada → sin auditoría)."""
    laboratorio = obtener_laboratorio(db, laboratorio_id)
    datos = _limpiar(datos)
    _validar(db, datos, excluir_id=laboratorio_id)
    anteriores = _campos(laboratorio)
    cambios = {c: v for c, v in datos.__dict__.items() if anteriores[c] != v}
    if not cambios:
        return laboratorio
    for campo, valor in cambios.items():
        setattr(laboratorio, campo, valor)
    antes = {campo: anteriores[campo] for campo in cambios}
    _auditar(db, actor, laboratorio_id, "editar_laboratorio", antes=antes, despues=cambios)
    return _confirmar(db, laboratorio)


def _tiene_entregas(db: Session, laboratorio_id: int) -> bool:
    """True si hay entregas del laboratorio o que usen alguna versión de su rúbrica."""
    versiones = (
        select(RubricaVersion.id)
        .join(Rubrica, RubricaVersion.rubrica_id == Rubrica.id)
        .where(Rubrica.laboratorio_id == laboratorio_id)
    )
    condicion = or_(
        Entrega.laboratorio_id == laboratorio_id, Entrega.rubrica_version_id.in_(versiones)
    )
    return bool(db.scalar(select(exists().where(condicion))))


def borrar_laboratorio(db: Session, laboratorio_id: int, actor: Perfil) -> None:
    """Borra el laboratorio con su rúbrica y versiones (y lo audita); 409 si tiene entregas."""
    laboratorio = obtener_laboratorio(db, laboratorio_id)
    if _tiene_entregas(db, laboratorio_id):
        raise ConflictoError(MSG_CON_ENTREGAS)
    antes = _campos(laboratorio)
    rubricas = select(Rubrica.id).where(Rubrica.laboratorio_id == laboratorio_id)
    try:
        borradas = db.execute(
            delete(RubricaVersion).where(RubricaVersion.rubrica_id.in_(rubricas))
        ).rowcount
        db.execute(delete(Rubrica).where(Rubrica.laboratorio_id == laboratorio_id))
        db.execute(delete(Laboratorio).where(Laboratorio.id == laboratorio_id))
        antes["versiones_rubrica_borradas"] = borradas or 0
        _auditar(db, actor, laboratorio_id, "borrar_laboratorio", antes=antes)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictoError(MSG_CON_ENTREGAS) from None
    except Exception:
        db.rollback()
        raise
