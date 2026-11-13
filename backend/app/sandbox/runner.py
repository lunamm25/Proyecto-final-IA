"""Sandbox para ejecutar código de estudiantes con validaciones y timeout."""

import io
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

BLOQUE_BYTES = 64 * 1024


def _resultado_error(mensaje: str) -> dict[str, Any]:
    """Resultado estándar cuando el ZIP se rechaza."""
    return {"error": mensaje, "stdout": "", "stderr": "", "codigo_salida": -1}


class SandboxRunner:
    """Ejecuta código Python de un ZIP en un directorio temporal con validaciones y timeout."""

    MAX_ZIP_SIZE = 20 * 1024 * 1024  # 20 MB
    MAX_FILES = 2000
    MAX_DECOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB
    TIMEOUT_SECONDS = 10

    def ejecutar_zip(self, archivo_zip: bytes) -> dict[str, Any]:
        """Valida, descomprime y ejecuta los .py de un ZIP.

        Retorna dict con stdout, stderr, codigo_salida y error (si ocurrió).
        """
        if len(archivo_zip) > self.MAX_ZIP_SIZE:
            return _resultado_error("ZIP demasiado grande")

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(io.BytesIO(archivo_zip)) as zf:
                    error = self._extraer(zf, Path(temp_dir).resolve())
            except zipfile.BadZipFile as e:
                return _resultado_error(f"ZIP inválido o corrupto: {e!s}")
            except OSError as e:
                return _resultado_error(f"Error al descomprimir: {e!s}")
            if error:
                return error
            return self._ejecutar_py(Path(temp_dir))

    def _extraer(self, zf: zipfile.ZipFile, destino: Path) -> dict[str, Any] | None:
        """Descomprime en bloques validando zip-slip y el tamaño real descomprimido."""
        miembros = zf.infolist()
        if len(miembros) > self.MAX_FILES:
            return _resultado_error("Demasiados archivos")

        total = 0
        for info in miembros:
            ruta = (destino / info.filename).resolve()
            if not ruta.is_relative_to(destino):
                return _resultado_error("ZIP sospechoso (zip-slip detectado)")
            if info.is_dir():
                ruta.mkdir(parents=True, exist_ok=True)
                continue
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as origen, ruta.open("wb") as salida:
                while bloque := origen.read(BLOQUE_BYTES):
                    total += len(bloque)
                    if total > self.MAX_DECOMPRESSED_SIZE:
                        return _resultado_error("Contenido demasiado grande")
                    salida.write(bloque)
        return None

    def _ejecutar_py(self, directorio: Path) -> dict[str, Any]:
        """Ejecuta cada .py del directorio con timeout y entorno vacío."""
        archivos_py = sorted(directorio.rglob("*.py"))
        if not archivos_py:
            return {
                "stdout": "",
                "stderr": "No se encontraron archivos .py en el ZIP",
                "codigo_salida": 0,
                "error": None,
            }

        stdout_total = ""
        stderr_total = ""
        codigo_salida = 0
        for archivo_py in archivos_py:
            try:
                resultado = subprocess.run(
                    [sys.executable, str(archivo_py)],
                    capture_output=True,
                    timeout=self.TIMEOUT_SECONDS,
                    text=True,
                    cwd=directorio,
                    env={},
                    check=False,
                )
            except subprocess.TimeoutExpired:
                stderr_total += f"Timeout después de {self.TIMEOUT_SECONDS} segundos\n"
                codigo_salida = -1
                break
            stdout_total += resultado.stdout
            stderr_total += resultado.stderr
            if resultado.returncode != 0:
                codigo_salida = resultado.returncode

        return {
            "stdout": stdout_total,
            "stderr": stderr_total,
            "codigo_salida": codigo_salida,
            "error": None,
        }
