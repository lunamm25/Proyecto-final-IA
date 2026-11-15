"""Dobles de prueba para entregas: almacén en memoria, PDF y ZIP generados en memoria.

Ningún doble usa la red ni el `.env`.
"""

import io
import zipfile

from app.services.almacen import AlmacenError


class AlmacenMemoria:
    """Almacén de archivos en memoria; puede fallar a partir de la subida número `fallar_en`."""

    def __init__(self, fallar_en: int | None = None) -> None:
        self.objetos: dict[str, bytes] = {}
        self.tipos: dict[str, str] = {}
        self.subidas: list[str] = []
        self.borrados: list[str] = []
        self.fallar_en = fallar_en

    def subir(self, ruta: str, datos: bytes, content_type: str) -> None:
        if self.fallar_en is not None and len(self.subidas) >= self.fallar_en:
            raise AlmacenError("Fallo simulado del almacén")
        self.subidas.append(ruta)
        self.objetos[ruta] = datos
        self.tipos[ruta] = content_type

    def descargar(self, ruta: str) -> bytes:
        if ruta not in self.objetos:
            raise AlmacenError("Archivo no encontrado en el almacén")
        return self.objetos[ruta]

    def borrar(self, rutas: list[str]) -> None:
        self.borrados.extend(rutas)
        for ruta in rutas:
            self.objetos.pop(ruta, None)


def pdf_con_texto(*lineas: str) -> bytes:
    """PDF mínimo válido (una página, Helvetica) con las líneas de texto indicadas."""
    partes = []
    for i, linea in enumerate(lineas):
        escapada = linea.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        partes.append(f"BT /F1 12 Tf 72 {720 - 20 * i} Td ({escapada}) Tj ET")
    contenido = "\n".join(partes).encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(contenido) + contenido + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida = b"%PDF-1.4\n"
    posiciones = []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % numero + objeto + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for posicion in posiciones:
        salida += b"%010d 00000 n \n" % posicion
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objetos) + 1,
        inicio_xref,
    )
    return salida


def pdf_sin_texto() -> bytes:
    """PDF válido con una página sin texto (como un escaneo sin OCR)."""
    return pdf_con_texto()


def zip_con(archivos: dict[str, str | bytes]) -> bytes:
    """ZIP en memoria con los archivos indicados (ruta → contenido)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for ruta, contenido in archivos.items():
            zf.writestr(ruta, contenido)
    return buffer.getvalue()
