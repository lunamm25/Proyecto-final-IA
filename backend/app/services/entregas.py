"""Entregas del portafolio (RF-04): validación de archivos, subida a Storage y listado por rol.

Orden al crear: validar todo → reservar el id (flush) → auditoría → subir archivos → commit.
Si la subida o el commit fallan se hace rollback y se borra lo subido (mejor esfuerzo).
Las rutas del bucket las genera el backend; nunca se usa el nombre de archivo del usuario.
"""

import io
import json
import logging
import re
import uuid
import zipfile
from dataclasses import dataclass
from typing import Any, BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Auditoria, Entrega, Evaluacion, Laboratorio, Perfil, RubricaVersion
from app.services.almacen import AlmacenArchivos, AlmacenError
from app.services.errores import (
    ArchivoDemasiadoGrandeError,
    DatosInvalidosError,
    NoEncontradoError,
    ServicioNoDisponibleError,
)
from app.services.material import MaterialIlegibleError, extraer_texto_pdf
from app.services.rubricas import obtener_version_vigente

logger = logging.getLogger(__name__)

MB = 1024 * 1024
BLOQUE_LECTURA = 1 * MB
LIMITE_PDF_BYTES = 20 * MB
LIMITE_ZIP_BYTES = 20 * MB
LIMITE_EXTRAS_CARACTERES = 4_000
MAX_CLAVES_EXTRAS = 20
MAX_TEXTO_EXTRA = 500
MAX_ARCHIVOS_ZIP = 2_000
MAX_DESCOMPRIMIDO_BYTES = 100 * MB
LIMITE_GITHUB_URL = 300
TIPOS_PDF = {"application/pdf", "application/x-pdf", "application/octet-stream"}
TIPOS_ZIP = {
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
    "application/octet-stream",
}
CLAVE_EXTRA = re.compile(r"[a-z0-9_]{1,40}")
PATRON_GITHUB = re.compile(
    r"https://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100})"
    r"(?P<resto>(?:/[A-Za-z0-9._-]+)*)/?"
)
ACCION_CREAR = "crear_entrega"
ACCION_FALLIDA = "crear_entrega_fallida"

MSG_FALTA_MATERIAL = (
    "Debes adjuntar al menos uno: el PDF del informe, el ZIP del código o la URL de GitHub."
)
MSG_LAB_NO_EXISTE = "El laboratorio no existe."
MSG_SIN_RUBRICA = "El laboratorio aún no tiene rúbrica aprobada; no se pueden recibir entregas."
MSG_PDF_GRANDE = "El PDF supera el tamaño máximo de 20 MB."
MSG_ZIP_GRANDE = "El ZIP supera el tamaño máximo de 20 MB."
MSG_PDF_TIPO = "El archivo del informe no es un PDF válido."
MSG_PDF_ILEGIBLE = "El PDF está dañado o protegido y no se puede leer."
MSG_PDF_SIN_TEXTO = (
    "El PDF no tiene texto extraíble (¿es un escaneo o una imagen?). "
    "Exporta el informe como PDF con texto seleccionable."
)
MSG_ZIP_TIPO = "El archivo del código no es un ZIP válido."
MSG_ZIP_ARCHIVOS = f"El ZIP tiene demasiados archivos (máximo {MAX_ARCHIVOS_ZIP})."
MSG_ZIP_DESCOMPRIMIDO = "El ZIP descomprimido supera el tamaño máximo de 100 MB."
MSG_GITHUB = (
    "La URL de GitHub no es válida: usa https://github.com/<usuario>/<repositorio>, "
    "sin credenciales, parámetros ni espacios."
)
MSG_EXTRAS = (
    f"El campo extras debe ser un objeto JSON pequeño (máximo {MAX_CLAVES_EXTRAS} claves en "
    f"minúscula y textos de hasta {MAX_TEXTO_EXTRA} caracteres)."
)
MSG_ALMACEN = "No se pudo guardar la entrega en este momento. Intenta de nuevo en unos minutos."
MSG_ESTUDIANTE_NO_EXISTE = "El estudiante no existe."


@dataclass(frozen=True)
class ArchivoEntrada:
    """Archivo recibido: flujo binario y content_type declarado (el nombre se ignora)."""

    flujo: BinaryIO
    content_type: str | None


@dataclass(frozen=True)
class FilaEntrega:
    """Entrega con su estudiante, laboratorio, versión de rúbrica y última evaluación."""

    entrega: Entrega
    estudiante: Perfil
    laboratorio: Laboratorio
    rubrica_version: RubricaVersion | None
    ultima_evaluacion: Evaluacion | None


@dataclass(frozen=True)
class PaginaEntregas:
    """Una página del listado y el total que cumple los filtros."""

    filas: list[FilaEntrega]
    total: int


# ---------- Validación ----------


def leer_limitado(flujo: Any, limite: int, mensaje: str) -> bytes:
    """Lee por bloques de 1 MB y rechaza (413) en cuanto se supera el límite."""
    partes: list[bytes] = []
    total = 0
    while bloque := flujo.read(BLOQUE_LECTURA):
        total += len(bloque)
        if total > limite:
            raise ArchivoDemasiadoGrandeError(mensaje)
        partes.append(bloque)
    return b"".join(partes)


def _tipo(content_type: str | None) -> str:
    """Content-Type sin parámetros y en minúscula."""
    return (content_type or "").split(";")[0].strip().lower()


def validar_github_url(url: str | None) -> str | None:
    """URL pública de un repositorio de GitHub (solo texto; el backend no clona nada)."""
    if url is None or not url.strip():
        return None
    url = url.strip(" ")
    coincidencia = PATRON_GITHUB.fullmatch(url) if len(url) <= LIMITE_GITHUB_URL else None
    if coincidencia is None:
        raise DatosInvalidosError(MSG_GITHUB)
    segmentos = [coincidencia["repo"], *coincidencia["resto"].split("/")]
    if any(s and set(s) == {"."} for s in segmentos):
        raise DatosInvalidosError(MSG_GITHUB)
    return url


def validar_extras(texto: str | None) -> dict[str, Any] | None:
    """Objeto JSON plano y pequeño (p. ej. enlaces a video o presentación); no va a la IA."""
    if texto is None or not texto.strip():
        return None
    if len(texto) > LIMITE_EXTRAS_CARACTERES:
        raise DatosInvalidosError(MSG_EXTRAS)
    try:
        datos = json.loads(texto)
    except ValueError:
        raise DatosInvalidosError(MSG_EXTRAS) from None
    if not isinstance(datos, dict) or len(datos) > MAX_CLAVES_EXTRAS:
        raise DatosInvalidosError(MSG_EXTRAS)
    for clave, valor in datos.items():
        valido = valor is None or isinstance(valor, bool | int | float)
        valido = valido or (isinstance(valor, str) and len(valor) <= MAX_TEXTO_EXTRA)
        if not CLAVE_EXTRA.fullmatch(clave) or not valido:
            raise DatosInvalidosError(MSG_EXTRAS)
    return datos or None


def validar_pdf(archivo: ArchivoEntrada) -> bytes:
    """PDF real (cabecera %PDF-), ≤ 20 MB y con texto extraíble (RF-04 CA2)."""
    if _tipo(archivo.content_type) not in TIPOS_PDF | {""}:
        raise DatosInvalidosError(MSG_PDF_TIPO)
    datos = leer_limitado(archivo.flujo, LIMITE_PDF_BYTES, MSG_PDF_GRANDE)
    if not datos.startswith(b"%PDF-"):
        raise DatosInvalidosError(MSG_PDF_TIPO)
    try:
        texto = extraer_texto_pdf(datos, limite=1)
    except MaterialIlegibleError:
        raise DatosInvalidosError(MSG_PDF_ILEGIBLE) from None
    if not texto.strip():
        raise DatosInvalidosError(MSG_PDF_SIN_TEXTO)
    return datos


def validar_zip(archivo: ArchivoEntrada) -> bytes:
    """ZIP real (cabecera PK\\x03\\x04 y zipfile válido), ≤ 20 MB y dentro de los límites de §9."""
    if _tipo(archivo.content_type) not in TIPOS_ZIP | {""}:
        raise DatosInvalidosError(MSG_ZIP_TIPO)
    datos = leer_limitado(archivo.flujo, LIMITE_ZIP_BYTES, MSG_ZIP_GRANDE)
    if not datos.startswith(b"PK\x03\x04") or not zipfile.is_zipfile(io.BytesIO(datos)):
        raise DatosInvalidosError(MSG_ZIP_TIPO)
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as zf:
            miembros = zf.infolist()
    except (zipfile.BadZipFile, OSError, ValueError):
        raise DatosInvalidosError(MSG_ZIP_TIPO) from None
    if len(miembros) > MAX_ARCHIVOS_ZIP:
        raise DatosInvalidosError(MSG_ZIP_ARCHIVOS)
    if sum(m.file_size for m in miembros) > MAX_DESCOMPRIMIDO_BYTES:
        raise DatosInvalidosError(MSG_ZIP_DESCOMPRIMIDO)
    return datos


def _version_para(db: Session, laboratorio_id: int) -> tuple[Laboratorio, RubricaVersion]:
    """Laboratorio y su versión de rúbrica vigente (422 si falta alguno)."""
    laboratorio = db.get(Laboratorio, laboratorio_id)
    if laboratorio is None:
        raise DatosInvalidosError(MSG_LAB_NO_EXISTE)
    version = obtener_version_vigente(db, laboratorio_id)
    if version is None:
        raise DatosInvalidosError(MSG_SIN_RUBRICA)
    return laboratorio, version


# ---------- Creación ----------


def _rutas(estudiante_id: uuid.UUID, entrega_id: int) -> tuple[str, str]:
    """Rutas del bucket generadas por el backend (nunca con el nombre del usuario)."""
    base = f"{estudiante_id}/{entrega_id}"
    return f"{base}/informe.pdf", f"{base}/codigo.zip"


def _borrar_subidos(almacen: AlmacenArchivos, rutas: list[str]) -> None:
    """Borra lo que se alcanzó a subir (mejor esfuerzo, nunca relanza)."""
    if not rutas:
        return
    try:
        almacen.borrar(rutas)
    except Exception as error:
        logger.warning("No se pudieron borrar archivos huérfanos (%s).", type(error).__name__)


def _auditar_fallo(
    db: Session, perfil: Perfil, entrega_id: int | None, error: Exception, settings: Settings
) -> None:
    """Registra el fallo del almacén o del commit con el detalle tachado (transacción aparte)."""
    from app.services.config_ia import tachar_secretos

    try:
        db.add(
            Auditoria(
                usuario_id=perfil.id,
                entidad="entregas",
                entidad_id=str(entrega_id or ""),
                accion=ACCION_FALLIDA,
                despues={
                    "tipo": type(error).__name__,
                    "detalle": tachar_secretos(str(error), settings),
                },
            )
        )
        db.commit()
    except Exception as segundo:
        db.rollback()
        logger.warning("No se pudo auditar el fallo de la entrega (%s).", type(segundo).__name__)


def crear_entrega(
    db: Session,
    perfil: Perfil,
    *,
    laboratorio_id: int,
    pdf: ArchivoEntrada | None,
    codigo_zip: ArchivoEntrada | None,
    github_url: str | None,
    extras: str | None,
    almacen: AlmacenArchivos,
    settings: Settings,
) -> FilaEntrega:
    """Valida, reserva el id, sube los archivos al bucket y confirma con auditoría."""
    url = validar_github_url(github_url)
    datos_extras = validar_extras(extras)
    if pdf is None and codigo_zip is None and url is None:
        raise DatosInvalidosError(MSG_FALTA_MATERIAL)
    laboratorio, version = _version_para(db, laboratorio_id)
    datos_pdf = validar_pdf(pdf) if pdf else None
    datos_zip = validar_zip(codigo_zip) if codigo_zip else None

    entrega = Entrega(
        estudiante_id=perfil.id,
        laboratorio_id=laboratorio.id,
        rubrica_version_id=version.id,
        github_url=url,
        extras=datos_extras,
    )
    db.add(entrega)
    db.flush()
    ruta_pdf, ruta_zip = _rutas(perfil.id, entrega.id)
    entrega.pdf_path = ruta_pdf if datos_pdf is not None else None
    entrega.codigo_zip_path = ruta_zip if datos_zip is not None else None
    db.add(
        Auditoria(
            usuario_id=perfil.id,
            entidad="entregas",
            entidad_id=str(entrega.id),
            accion=ACCION_CREAR,
            despues={
                "laboratorio_id": laboratorio.id,
                "rubrica_version_id": version.id,
                "tiene_pdf": datos_pdf is not None,
                "tiene_zip": datos_zip is not None,
                "github_url": url,
                "tamano_pdf": len(datos_pdf) if datos_pdf is not None else None,
                "tamano_zip": len(datos_zip) if datos_zip is not None else None,
                "tiene_extras": datos_extras is not None,
            },
        )
    )
    entrega_id = entrega.id
    subidos: list[str] = []
    try:
        if datos_pdf is not None:
            almacen.subir(ruta_pdf, datos_pdf, "application/pdf")
            subidos.append(ruta_pdf)
        if datos_zip is not None:
            almacen.subir(ruta_zip, datos_zip, "application/zip")
            subidos.append(ruta_zip)
        db.commit()
    except Exception as error:
        db.rollback()
        _borrar_subidos(almacen, subidos)
        if isinstance(error, AlmacenError):
            logger.warning("Falló la subida de la entrega %s al almacén.", entrega_id)
        else:
            logger.warning(
                "Falló el guardado de la entrega %s (%s).", entrega_id, type(error).__name__
            )
        _auditar_fallo(db, perfil, entrega_id, error, settings)
        raise ServicioNoDisponibleError(MSG_ALMACEN) from None
    db.refresh(entrega)
    return FilaEntrega(entrega, perfil, laboratorio, version, None)


# ---------- Listado ----------


def _ultimas_evaluaciones(db: Session, entrega_ids: list[int]) -> dict[int, Evaluacion]:
    """Última evaluación de cada entrega (por fecha y luego id)."""
    if not entrega_ids:
        return {}
    consulta = (
        select(Evaluacion)
        .where(Evaluacion.entrega_id.in_(entrega_ids))
        .order_by(Evaluacion.creada_en.desc(), Evaluacion.id.desc())
    )
    ultimas: dict[int, Evaluacion] = {}
    for evaluacion in db.scalars(consulta):
        ultimas.setdefault(evaluacion.entrega_id, evaluacion)
    return ultimas


def listar_entregas(
    db: Session,
    perfil: Perfil,
    *,
    estudiante_id: uuid.UUID | None,
    laboratorio_id: int | None,
    limit: int,
    offset: int,
) -> PaginaEntregas:
    """Portafolio: el estudiante solo lo suyo (otro id → 404); docente/admin, cualquiera."""
    if perfil.rol not in ("docente", "admin"):
        if estudiante_id is not None and estudiante_id != perfil.id:
            raise NoEncontradoError(MSG_ESTUDIANTE_NO_EXISTE)
        estudiante_id = perfil.id
    filtros = []
    if estudiante_id is not None:
        filtros.append(Entrega.estudiante_id == estudiante_id)
    if laboratorio_id is not None:
        filtros.append(Entrega.laboratorio_id == laboratorio_id)
    total = db.scalar(select(func.count(Entrega.id)).where(*filtros)) or 0
    consulta = (
        select(Entrega, Perfil, Laboratorio, RubricaVersion)
        .join(Perfil, Entrega.estudiante_id == Perfil.id)
        .join(Laboratorio, Entrega.laboratorio_id == Laboratorio.id)
        .outerjoin(RubricaVersion, Entrega.rubrica_version_id == RubricaVersion.id)
        .where(*filtros)
        .order_by(Entrega.creada_en.desc(), Entrega.id.desc())
        .limit(limit)
        .offset(offset)
    )
    filas = db.execute(consulta).all()
    ultimas = _ultimas_evaluaciones(db, [fila[0].id for fila in filas])
    return PaginaEntregas(
        [FilaEntrega(e, p, lab, v, ultimas.get(e.id)) for e, p, lab, v in filas], total
    )
