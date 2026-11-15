"""Almacén de archivos de las entregas: bucket privado de Supabase Storage vía su API REST.

La interfaz `AlmacenArchivos` es inyectable (los tests usan un doble en memoria). Los errores
nunca incluyen la clave de servicio ni la URL del proyecto: el mensaje se tacha con
`tachar_secretos` y la excepción original no se encadena.
"""

import re
from typing import Protocol
from urllib.parse import quote

import httpx

from app.config import Settings
from app.services.secretos import tachar_secretos

TIMEOUT_SEGUNDOS = 30.0
LIMITE_DESCARGA_BYTES = 25 * 1024 * 1024
PATRON_RUTA = re.compile(
    r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]+)?(?:/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]+)?)*"
)
MSG_NO_CONFIGURADO = "El almacén de archivos no está configurado en el servidor."


class AlmacenError(Exception):
    """Fallo del almacén; el mensaje ya viene sin secretos (solo para auditoría)."""


class AlmacenArchivos(Protocol):
    """Operaciones mínimas sobre el bucket privado de entregas."""

    def subir(self, ruta: str, datos: bytes, content_type: str) -> None: ...

    def descargar(self, ruta: str) -> bytes: ...

    def borrar(self, rutas: list[str]) -> None: ...


def validar_ruta(ruta: str) -> str:
    """Acepta solo rutas generadas por el backend (segmentos simples, sin `..` ni `/` inicial)."""
    if not PATRON_RUTA.fullmatch(ruta or ""):
        raise AlmacenError("Ruta de almacén no válida.")
    return ruta


class AlmacenSupabase:
    """Implementación real contra la API REST de Supabase Storage (con timeout)."""

    def __init__(
        self,
        settings: Settings,
        transporte: httpx.BaseTransport | None = None,
        timeout: float = TIMEOUT_SEGUNDOS,
    ) -> None:
        self._settings = settings
        self._base = settings.supabase_url.strip().rstrip("/")
        self._clave = settings.supabase_service_key.strip()
        self._bucket = settings.supabase_bucket.strip()
        self._transporte = transporte
        self._timeout = timeout

    def _cliente(self) -> httpx.Client:
        """Cliente HTTP con las cabeceras de autenticación del servicio."""
        if not (self._base and self._clave and self._bucket):
            raise AlmacenError(MSG_NO_CONFIGURADO)
        return httpx.Client(
            base_url=f"{self._base}/storage/v1",
            headers={"Authorization": f"Bearer {self._clave}", "apikey": self._clave},
            timeout=self._timeout,
            transport=self._transporte,
            follow_redirects=False,
        )

    def _url_objeto(self, ruta: str) -> str:
        """Ruta relativa del objeto dentro del bucket."""
        return f"/object/{quote(self._bucket, safe='')}/{quote(validar_ruta(ruta), safe='/')}"

    def _fallo(self, operacion: str, error: Exception | None, codigo: int | None) -> AlmacenError:
        """Error tachado (sin clave, URL ni tokens) para guardar en auditoría."""
        partes = [f"Fallo al {operacion} en el almacén"]
        if codigo is not None:
            partes.append(f"(HTTP {codigo})")
        if error is not None:
            partes.append(f"{type(error).__name__}: {error}")
        return AlmacenError(tachar_secretos(" ".join(partes), self._settings))

    def subir(self, ruta: str, datos: bytes, content_type: str) -> None:
        """Sube el archivo sin sobrescribir (x-upsert: false)."""
        url = self._url_objeto(ruta)
        try:
            with self._cliente() as cliente:
                respuesta = cliente.post(
                    url,
                    content=datos,
                    headers={"Content-Type": content_type, "x-upsert": "false"},
                )
        except httpx.HTTPError as error:
            raise self._fallo("subir", error, None) from None
        if respuesta.status_code >= 300:
            raise self._fallo("subir", None, respuesta.status_code)

    def descargar(self, ruta: str) -> bytes:
        """Descarga el archivo leyendo por partes, con un tamaño máximo."""
        url = self._url_objeto(ruta)
        try:
            with self._cliente() as cliente, cliente.stream("GET", url) as respuesta:
                if respuesta.status_code >= 300:
                    raise self._fallo("descargar", None, respuesta.status_code)
                partes: list[bytes] = []
                total = 0
                for bloque in respuesta.iter_bytes():
                    total += len(bloque)
                    if total > LIMITE_DESCARGA_BYTES:
                        raise self._fallo("descargar (archivo demasiado grande)", None, None)
                    partes.append(bloque)
        except httpx.HTTPError as error:
            raise self._fallo("descargar", error, None) from None
        return b"".join(partes)

    def borrar(self, rutas: list[str]) -> None:
        """Borra varios objetos del bucket."""
        if not rutas:
            return
        validas = [validar_ruta(r) for r in rutas]
        try:
            with self._cliente() as cliente:
                respuesta = cliente.request(
                    "DELETE",
                    f"/object/{quote(self._bucket, safe='')}",
                    json={"prefixes": validas},
                )
        except httpx.HTTPError as error:
            raise self._fallo("borrar", error, None) from None
        if respuesta.status_code >= 300:
            raise self._fallo("borrar", None, respuesta.status_code)
