"""Sandbox seguro para ejecutar código de estudiantes con límites de recursos."""

import io
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


class SandboxRunner:
    """Ejecuta código Python en un entorno aislado con validaciones y límites."""

    MAX_ZIP_SIZE = 20 * 1024 * 1024  # 20 MB
    MAX_FILES = 2000
    MAX_DECOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB
    TIMEOUT_SECONDS = 10

    def ejecutar_zip(self, archivo_zip: bytes) -> dict[str, Any]:
        """Ejecuta código Python dentro de un ZIP con límites de seguridad.

        Retorna dict con stdout, stderr, codigo_salida y error (si ocurrió).
        """
        # Validación 1: tamaño del ZIP
        if len(archivo_zip) > self.MAX_ZIP_SIZE:
            return {"error": "ZIP demasiado grande", "stdout": "", "stderr": "", "codigo_salida": -1}

        # Validación 2 y 3: validar ZIP, contar archivos y tamaño descomprimido
        try:
            validacion = self._validar_zip(archivo_zip)
            if validacion.get("error"):
                return validacion
        except zipfile.BadZipFile as e:
            return {
                "error": f"ZIP inválido o corrupto: {e!s}",
                "stdout": "",
                "stderr": "",
                "codigo_salida": -1,
            }

        # Ejecutar código en directorio temporal
        return self._ejecutar_en_temp(archivo_zip)

    def _validar_zip(self, archivo_zip: bytes) -> dict[str, Any]:
        """Valida límites y protección contra zip-slip y zip-bomb.

        Retorna dict con error si falla, caso contrario dict vacío.
        """
        try:
            zip_bytes = io.BytesIO(archivo_zip)
            with zipfile.ZipFile(zip_bytes, "r") as zf:
                # Validación: número de archivos
                nombres = zf.namelist()
                if len(nombres) > self.MAX_FILES:
                    return {"error": "Demasiados archivos", "stdout": "", "stderr": "", "codigo_salida": -1}

                # Validación: tamaño descomprimido y zip-slip
                tamaño_total = 0
                for info in zf.infolist():
                    # Validación: zip-slip (rutas que salen del directorio temporal)
                    nombre_normalizado = os.path.normpath(info.filename)
                    if nombre_normalizado.startswith("..") or os.path.isabs(nombre_normalizado):
                        return {"error": "ZIP sospechoso (zip-slip detectado)", "stdout": "", "stderr": "", "codigo_salida": -1}

                    tamaño_total += info.file_size

                if tamaño_total > self.MAX_DECOMPRESSED_SIZE:
                    return {"error": "Contenido demasiado grande", "stdout": "", "stderr": "", "codigo_salida": -1}

            return {}  # Validación exitosa
        except zipfile.BadZipFile as e:
            return {"error": f"ZIP corrupto: {e!s}", "stdout": "", "stderr": "", "codigo_salida": -1}

    def _ejecutar_en_temp(self, archivo_zip: bytes) -> dict[str, Any]:
        """Descomprime el ZIP en un directorio temporal y ejecuta todos los .py encontrados."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Descomprimir ZIP
                zip_bytes = io.BytesIO(archivo_zip)
                with zipfile.ZipFile(zip_bytes, "r") as zf:
                    zf.extractall(temp_dir)

                # Buscar todos los archivos .py
                archivos_py = list(Path(temp_dir).rglob("*.py"))

                if not archivos_py:
                    return {
                        "stdout": "",
                        "stderr": "No se encontraron archivos .py en el ZIP",
                        "codigo_salida": 0,
                        "error": None,
                    }

                # Ejecutar el primer archivo .py encontrado (o todos si se necesita)
                # Por simplicidad, ejecutamos todos en orden
                stdout_total = ""
                stderr_total = ""
                codigo_salida = 0

                for archivo_py in sorted(archivos_py):
                    try:
                        resultado = subprocess.run(
                            [sys.executable, str(archivo_py)],
                            capture_output=True,
                            timeout=self.TIMEOUT_SECONDS,
                            text=True,
                            cwd=temp_dir,
                            env={},  # Entorno vacío, sin variables secretas
                            check=False,
                        )
                        stdout_total += resultado.stdout
                        stderr_total += resultado.stderr
                        codigo_salida = resultado.returncode if resultado.returncode != 0 else codigo_salida
                    except subprocess.TimeoutExpired:
                        stderr_total += f"Timeout después de {self.TIMEOUT_SECONDS} segundos\n"
                        codigo_salida = -1
                        break

                return {
                    "stdout": stdout_total,
                    "stderr": stderr_total,
                    "codigo_salida": codigo_salida,
                    "error": None,
                }

            except (OSError, ValueError) as e:
                return {
                    "stdout": "",
                    "stderr": "",
                    "codigo_salida": -1,
                    "error": f"Error al ejecutar: {e!s}",
                }
