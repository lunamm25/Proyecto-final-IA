"""Material de una entrega que se envía a la IA y saneamiento de la verificación técnica.

`obtener_material` descarga del almacén el PDF y el ZIP de la entrega, extrae el texto del
informe (pypdf) y los `.py` del ZIP (sin extraer a disco, con protección contra zip-slip y
zip-bomb), quita correos y el nombre del estudiante y trunca a un tamaño fijo. Si
`VERIFICACION_ACTIVA` está encendida, ejecuta el ZIP con el SandboxRunner de Rol 4 y guarda
solo un resumen de 3 campos (nunca stdout ni stderr).
No se usa `entrega.extras` porque lo escribe el estudiante y no es confiable.
"""

import io
import logging
import math
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models import Entrega, Perfil
from app.services.almacen import AlmacenArchivos

logger = logging.getLogger(__name__)

CLAVE_METRICA = re.compile(r"^[a-z0-9_]{1,40}$")
PROFUNDIDAD_MAXIMA = 8

# Mismos topes que usa el prompt del evaluador de Rol 1 (app/ia/evaluador.py): enviar más
# texto no lo vería el modelo. Incluyen la nota de truncado.
LIMITE_INFORME = 30_000
LIMITE_CODIGO = 12_000
MAX_PAGINAS_PDF = 300
MAX_ARCHIVOS_ZIP = 2_000
MAX_DESCOMPRIMIDO_BYTES = 100 * 1024 * 1024
BLOQUE_ZIP = 64 * 1024
CARPETAS_IGNORADAS = {
    "__macosx",
    "__pycache__",
    "venv",
    "env",
    "site-packages",
    "node_modules",
}
PATRON_CORREO = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NOTA_TRUNCADO = "\n[... {} truncado: se envían solo los primeros {} caracteres]"
CAMPOS_VERIFICACION = ("codigo_salida", "tiene_error", "ejecucion_exitosa")
VERIFICACION_FALLIDA = {"codigo_salida": -1, "tiene_error": True, "ejecucion_exitosa": False}


class MaterialIlegibleError(Exception):
    """El PDF o el ZIP no se pueden leer."""


class ZipInseguroError(MaterialIlegibleError):
    """El ZIP supera los límites de archivos o de tamaño descomprimido (posible zip-bomb)."""


@dataclass(frozen=True)
class Material:
    """Texto del informe, resumen del código y resultados de la verificación técnica."""

    texto_informe: str = ""
    resumen_codigo: str | None = None
    resultados_verificacion: Any = None


CargadorMaterial = Callable[[Session, Entrega], Material]
EjecutorCodigo = Callable[[bytes], dict[str, Any]]
"""Ejecuta un ZIP en el sandbox (SandboxRunner().ejecutar_zip); inyectable en los tests."""


# ---------- PDF ----------


def extraer_texto_pdf(datos: bytes, limite: int | None = None) -> str:
    """Texto de las páginas del PDF (se detiene al superar `limite` caracteres)."""
    try:
        lector = PdfReader(io.BytesIO(datos))
        if lector.is_encrypted and not lector.decrypt(""):
            raise MaterialIlegibleError("El PDF está protegido con contraseña.")
        partes: list[str] = []
        total = 0
        for indice, pagina in enumerate(lector.pages):
            if indice >= MAX_PAGINAS_PDF or (limite is not None and total > limite):
                break
            texto = pagina.extract_text() or ""
            partes.append(texto)
            total += len(texto)
    except MaterialIlegibleError:
        raise
    except Exception as error:  # pypdf lanza muchos tipos distintos ante PDF dañados
        raise MaterialIlegibleError(f"PDF ilegible ({type(error).__name__}).") from None
    return "\n".join(partes).replace("\x00", "").strip()


# ---------- ZIP ----------


def _ruta_segura(nombre: str) -> str | None:
    """Ruta relativa normalizada del miembro o None si es absoluta, con `..` o de entorno."""
    nombre = nombre.replace("\\", "/")
    if nombre.startswith("/") or re.match(r"^[A-Za-z]:", nombre):
        return None
    partes = PurePosixPath(nombre).parts
    if not partes or any(p in ("..", ".") for p in partes):
        return None
    if any(p.lower() in CARPETAS_IGNORADAS or p.startswith(".") for p in partes[:-1]):
        return None
    return "/".join(partes)


def _abrir_zip(datos: bytes) -> zipfile.ZipFile:
    """Abre el ZIP y comprueba nº de archivos y tamaño descomprimido declarado."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(datos))
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        raise MaterialIlegibleError(f"ZIP ilegible ({type(error).__name__}).") from None
    miembros = zf.infolist()
    if len(miembros) > MAX_ARCHIVOS_ZIP:
        zf.close()
        raise ZipInseguroError(f"El ZIP tiene más de {MAX_ARCHIVOS_ZIP} archivos.")
    if sum(m.file_size for m in miembros) > MAX_DESCOMPRIMIDO_BYTES:
        zf.close()
        raise ZipInseguroError("El ZIP descomprimido supera el tamaño máximo.")
    return zf


def _leer_miembro(zf: zipfile.ZipFile, info: zipfile.ZipInfo, maximo: int) -> bytes:
    """Lee hasta `maximo` bytes descomprimidos del miembro, por bloques."""
    partes: list[bytes] = []
    total = 0
    with zf.open(info) as origen:
        while total < maximo and (bloque := origen.read(min(BLOQUE_ZIP, maximo - total))):
            partes.append(bloque)
            total += len(bloque)
    return b"".join(partes)


def extraer_codigo_zip(datos: bytes) -> str:
    """Archivos `.py` del ZIP concatenados con un encabezado por archivo, truncados."""
    bloques: list[str] = []
    longitud = 0
    leidos = 0
    truncado = False
    try:
        with _abrir_zip(datos) as zf:
            candidatos = []
            for info in zf.infolist():
                ruta = None if info.is_dir() else _ruta_segura(info.filename)
                if ruta and ruta.lower().endswith(".py"):
                    candidatos.append((ruta, info))
            for ruta, info in sorted(candidatos, key=lambda par: par[0]):
                restante = LIMITE_CODIGO - longitud
                if restante <= 0:
                    truncado = True
                    break
                maximo = min(restante * 4 + 4, MAX_DESCOMPRIMIDO_BYTES - leidos)
                crudo = _leer_miembro(zf, info, maximo)
                leidos += len(crudo)
                texto = crudo.decode("utf-8", errors="replace").replace("\x00", "")
                bloque = f"### Archivo: {ruta}\n{texto.rstrip()}\n\n"
                bloques.append(bloque)
                longitud += len(bloque)
                if len(crudo) >= maximo or longitud > LIMITE_CODIGO:
                    truncado = True
                    break
    except MaterialIlegibleError:
        raise
    except (zipfile.BadZipFile, OSError, ValueError, RuntimeError, EOFError) as error:
        raise MaterialIlegibleError(f"ZIP ilegible ({type(error).__name__}).") from None
    return _truncar("".join(bloques).strip(), LIMITE_CODIGO, "código", forzar_nota=truncado)


# ---------- Saneamiento y truncado ----------


def _truncar(texto: str, limite: int, que: str, forzar_nota: bool = False) -> str:
    """Recorta a `limite` caracteres (incluida la nota de truncado) y lo anota."""
    if len(texto) <= limite and not forzar_nota:
        return texto
    nota = NOTA_TRUNCADO.format(que, limite)
    return texto[: max(limite - len(nota), 0)] + nota


def sanear_texto(texto: str, nombre: str | None, correo: str | None) -> str:
    """Quita el correo y el nombre del estudiante ("[estudiante]") y otros correos ("[correo]").

    Limitación: otros nombres propios (compañeros, docentes) no se detectan de forma fiable.
    """
    if correo and correo.strip():
        texto = re.sub(re.escape(correo.strip()), "[estudiante]", texto, flags=re.IGNORECASE)
    texto = PATRON_CORREO.sub("[correo]", texto)
    if nombre and nombre.strip():
        completo = r"\s+".join(re.escape(p) for p in nombre.split())
        texto = re.sub(rf"\b{completo}\b", "[estudiante]", texto, flags=re.IGNORECASE)
    return texto


# ---------- Verificación técnica ----------


def resumen_verificacion(datos: Any) -> dict[str, Any] | None:
    """Solo los 3 campos del resumen de ejecución (o None si no están o tienen otro tipo)."""
    if not isinstance(datos, dict):
        return None
    codigo = datos.get("codigo_salida")
    tiene_error = datos.get("tiene_error")
    exitosa = datos.get("ejecucion_exitosa")
    if (
        not isinstance(codigo, int)
        or isinstance(codigo, bool)
        or not isinstance(tiene_error, bool)
        or not isinstance(exitosa, bool)
    ):
        return None
    return {"codigo_salida": codigo, "tiene_error": tiene_error, "ejecucion_exitosa": exitosa}


def _verificar(datos_zip: bytes, ejecutar: EjecutorCodigo) -> dict[str, Any]:
    """Ejecuta el ZIP en el sandbox y resume el resultado (descarta stdout y stderr)."""
    try:
        salida = ejecutar(datos_zip)
    except Exception as error:  # un fallo del sandbox no debe tumbar la evaluación
        logger.warning("La verificación técnica falló (%s).", type(error).__name__)
        return dict(VERIFICACION_FALLIDA)
    codigo = salida.get("codigo_salida") if isinstance(salida, dict) else None
    if not isinstance(codigo, int) or isinstance(codigo, bool):
        return dict(VERIFICACION_FALLIDA)
    tiene_error = salida.get("error") is not None
    return {
        "codigo_salida": codigo,
        "tiene_error": tiene_error,
        "ejecucion_exitosa": not tiene_error and codigo == 0,
    }


# ---------- Material completo ----------


def obtener_material(
    db: Session,
    entrega: Entrega,
    *,
    almacen: AlmacenArchivos,
    verificacion_activa: bool,
    ejecutar: EjecutorCodigo,
) -> Material:
    """Descarga, extrae, sanea y trunca el material de la entrega (y verifica si está activo)."""
    perfil = db.get(Perfil, entrega.estudiante_id)
    nombre = perfil.nombre if perfil else None
    correo = perfil.correo if perfil else None
    texto_informe = ""
    if entrega.pdf_path:
        crudo = extraer_texto_pdf(almacen.descargar(entrega.pdf_path), limite=LIMITE_INFORME * 2)
        texto_informe = _truncar(sanear_texto(crudo, nombre, correo), LIMITE_INFORME, "informe")
    resumen_codigo: str | None = None
    verificacion: dict[str, Any] | None = None
    if entrega.codigo_zip_path:
        datos_zip = almacen.descargar(entrega.codigo_zip_path)
        codigo = sanear_texto(extraer_codigo_zip(datos_zip), nombre, correo)
        resumen_codigo = _truncar(codigo, LIMITE_CODIGO, "código") or None
        if verificacion_activa:
            verificacion = _verificar(datos_zip, ejecutar)
    return Material(texto_informe, resumen_codigo, verificacion)


def _limpiar(valor: Any, profundidad: int) -> Any:
    """Devuelve el valor filtrado (solo números finitos y booleanos) o None si se descarta."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if profundidad >= PROFUNDIDAD_MAXIMA:
        return None
    if isinstance(valor, dict):
        limpio = {
            clave: interno
            for clave, interno in (
                (c, _limpiar(v, profundidad + 1))
                for c, v in valor.items()
                if isinstance(c, str) and CLAVE_METRICA.fullmatch(c)
            )
            if interno is not None
        }
        return limpio or None
    if isinstance(valor, list | tuple):
        lista = [v for v in (_limpiar(x, profundidad + 1) for x in valor) if v is not None]
        return lista or None
    return None


def sanear_verificacion(datos: Any) -> dict[str, Any]:
    """Deja solo números y booleanos con claves cortas de métrica; descarta todo texto libre."""
    if not isinstance(datos, dict):
        return {}
    return _limpiar(datos, 0) or {}
