"""Utilidades comunes para archivos subidos: lectura por bloques con tope y validación de PDF.

Las usan las entregas (RF-04) y la extracción de rúbricas (RF-03 CA1). Cada uso pasa sus
propios mensajes para que el usuario sepa de qué archivo se habla.
"""

from dataclasses import dataclass
from typing import Any, BinaryIO

from app.services.errores import ArchivoDemasiadoGrandeError, DatosInvalidosError
from app.services.material import MaterialIlegibleError, extraer_texto_pdf

MB = 1024 * 1024
BLOQUE_LECTURA = 1 * MB
LIMITE_PDF_BYTES = 20 * MB
TIPOS_PDF = {"application/pdf", "application/x-pdf", "application/octet-stream"}


@dataclass(frozen=True)
class ArchivoEntrada:
    """Archivo recibido: flujo binario y content_type declarado (el nombre se ignora)."""

    flujo: BinaryIO
    content_type: str | None


@dataclass(frozen=True)
class MensajesPdf:
    """Mensajes en español para cada motivo de rechazo de un PDF."""

    grande: str
    tipo: str
    ilegible: str
    sin_texto: str


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


def tipo_contenido(content_type: str | None) -> str:
    """Content-Type sin parámetros y en minúscula."""
    return (content_type or "").split(";")[0].strip().lower()


def validar_pdf(
    archivo: ArchivoEntrada, mensajes: MensajesPdf, limite: int = LIMITE_PDF_BYTES
) -> bytes:
    """PDF real (cabecera %PDF-), ≤ `limite` bytes y con texto extraíble; devuelve sus bytes."""
    if tipo_contenido(archivo.content_type) not in TIPOS_PDF | {""}:
        raise DatosInvalidosError(mensajes.tipo)
    datos = leer_limitado(archivo.flujo, limite, mensajes.grande)
    if not datos.startswith(b"%PDF-"):
        raise DatosInvalidosError(mensajes.tipo)
    try:
        texto = extraer_texto_pdf(datos, limite=1)
    except MaterialIlegibleError:
        raise DatosInvalidosError(mensajes.ilegible) from None
    if not texto.strip():
        raise DatosInvalidosError(mensajes.sin_texto)
    return datos
