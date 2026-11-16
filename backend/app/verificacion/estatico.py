"""Análisis estático del código de una entrega (RF-06 CA1, CA3 y CA4). Nunca ejecuta el código.

Lee el ZIP en memoria con límites (nº de archivos, tamaño por archivo y total, zip-slip) y, para
cada `.py` y para las celdas de código de los cuadernos `.ipynb`, calcula:

- sintaxis con `ast.parse` (solo construye el árbol, no ejecuta nada);
- hallazgos de `ruff` con sus reglas por defecto (E4, E7, E9 y F) y `--isolated`, para no leer
  ninguna configuración que venga dentro del ZIP;
- complejidad ciclomática con `radon cc`;
- métricas: archivos, líneas y presencia de README, requirements y tests.

Devuelve dos vistas:

- `resumen`: solo números y booleanos con claves cortas. Es lo único que llega a la IA, así que
  ningún texto del estudiante (nombres de archivo, mensajes) entra al prompt.
- `detalle`: para las columnas de `verificaciones_codigo` (rutas, líneas y códigos de regla,
  recortados). No se expone en la API ni se envía al modelo.

Los tests del estudiante no se ejecutan aquí; ejecutar código solo lo hace el sandbox cuando
`VERIFICACION_ACTIVA=true`. Para otros lenguajes solo hay conteos (RF-06 CA4).
"""

import ast
import io
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import warnings
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from radon.complexity import cc_visit
from radon.visitors import Class

logger = logging.getLogger(__name__)

MAX_ARCHIVOS_ZIP = 2_000
MAX_DESCOMPRIMIDO_BYTES = 100 * 1024 * 1024
MAX_ARCHIVOS_ANALIZADOS = 300
MAX_BYTES_PY = 1024 * 1024
MAX_BYTES_NOTEBOOK = 8 * 1024 * 1024
MAX_BYTES_ANALIZADOS = 20 * 1024 * 1024
MAX_ITEMS_DETALLE = 30
LIMITE_MENSAJE = 160
TIMEOUT_RUFF_SEGUNDOS = 30
UMBRAL_COMPLEJIDAD_ALTA = 10
BLOQUE_ZIP = 64 * 1024
REGLAS_RUFF = "E4,E7,E9,F"

CARPETAS_IGNORADAS = {
    "__macosx",
    "__pycache__",
    ".git",
    ".ipynb_checkpoints",
    ".venv",
    "env",
    "node_modules",
    "site-packages",
    "venv",
}
EXTENSIONES_OTROS = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js", ".jsx", ".kt", ".m",
    ".php", ".r", ".rb", ".rs", ".scala", ".sh", ".sql", ".swift", ".ts", ".tsx",
}  # fmt: skip
NOMBRES_REQUIREMENTS = {
    "environment.yaml",
    "environment.yml",
    "pipfile",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
}
# Errores que impiden ejecutar o que casi seguro son fallos (no estilo): sintaxis, nombres no
# definidos, comparaciones con literales mal hechas, redefiniciones.
CODIGOS_GRAVES = {"F632", "F811", "F821", "F822", "F823"}
VARIABLES_ENTORNO_RUFF = {"PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG", "LC_ALL"}
PATRON_MAGIA = re.compile(r"^(\s*)[%!].*$")


@dataclass(frozen=True)
class ResultadoEstatico:
    """`resumen` (números y booleanos, para la IA) y `detalle` (para verificaciones_codigo)."""

    resumen: dict[str, Any]
    detalle: dict[str, Any]


@dataclass
class _Inventario:
    archivos: int = 0
    python: int = 0
    notebooks: int = 0
    otros: int = 0
    omitidos: int = 0
    readme: bool = False
    requirements: bool = False
    carpeta_tests: bool = False


# ---------- Lectura segura del ZIP ----------


def _ruta_segura(nombre: str) -> str | None:
    """Ruta relativa normalizada, o None si es absoluta, con `..` o en carpeta ignorada."""
    nombre = nombre.replace("\\", "/")
    if nombre.startswith("/") or re.match(r"^[A-Za-z]:", nombre):
        return None
    partes = PurePosixPath(nombre).parts
    if not partes or any(p in ("..", ".") for p in partes):
        return None
    if any(p.lower() in CARPETAS_IGNORADAS or p.startswith(".") for p in partes[:-1]):
        return None
    return "/".join(partes)


def _leer(zf: zipfile.ZipFile, info: zipfile.ZipInfo, maximo: int) -> bytes:
    """Lee como mucho `maximo` bytes descomprimidos del miembro, por bloques."""
    partes: list[bytes] = []
    total = 0
    with zf.open(info) as origen:
        while total < maximo and (bloque := origen.read(min(BLOQUE_ZIP, maximo - total))):
            partes.append(bloque)
            total += len(bloque)
    return b"".join(partes)


def codigo_de_notebook(texto: str) -> str:
    """Celdas de código de un `.ipynb`; las líneas mágicas (`%`, `!`) se cambian por `pass`."""
    try:
        cuaderno = json.loads(texto)
    except ValueError:
        return ""
    celdas = cuaderno.get("cells") if isinstance(cuaderno, dict) else None
    if not isinstance(celdas, list):
        return ""
    bloques: list[str] = []
    for celda in celdas:
        if not isinstance(celda, dict) or celda.get("cell_type") != "code":
            continue
        fuente = celda.get("source", "")
        if isinstance(fuente, list):
            fuente = "".join(parte for parte in fuente if isinstance(parte, str))
        if not isinstance(fuente, str):
            continue
        lineas = [PATRON_MAGIA.sub(_sin_magia, linea) for linea in fuente.splitlines()]
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques) + ("\n" if bloques else "")


def _sin_magia(coincidencia: re.Match[str]) -> str:
    """Una línea mágica sangrada pasa a `pass` (el bloque sigue siendo válido); si no, se vacía."""
    sangria = coincidencia.group(1)
    return f"{sangria}pass" if sangria else ""


def _clasificar(inventario: _Inventario, ruta: str) -> str:
    """Actualiza el inventario con el archivo y devuelve su tipo: python, notebook u otro."""
    camino = PurePosixPath(ruta)
    nombre = camino.name.lower()
    sufijo = camino.suffix.lower()
    inventario.archivos += 1
    if nombre.startswith("readme"):
        inventario.readme = True
    if (nombre.startswith("requirements") and sufijo == ".txt") or nombre in NOMBRES_REQUIREMENTS:
        inventario.requirements = True
    if any(p.lower() in ("test", "tests") for p in camino.parts[:-1]):
        inventario.carpeta_tests = True
    if sufijo == ".py":
        inventario.python += 1
        return "python"
    if sufijo == ".ipynb":
        inventario.notebooks += 1
        return "notebook"
    if sufijo in EXTENSIONES_OTROS:
        inventario.otros += 1
    return "otro"


def _leer_fuentes(datos: bytes) -> tuple[dict[str, str], _Inventario]:
    """Código Python del ZIP (ruta → texto) e inventario de archivos. ValueError si es ilegible."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(datos))
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        raise ValueError(f"ZIP ilegible ({type(error).__name__}).") from None
    fuentes: dict[str, str] = {}
    inventario = _Inventario()
    leidos = 0
    with zf:
        miembros = zf.infolist()
        if len(miembros) > MAX_ARCHIVOS_ZIP:
            raise ValueError("El ZIP tiene demasiados archivos.")
        if sum(m.file_size for m in miembros) > MAX_DESCOMPRIMIDO_BYTES:
            raise ValueError("El ZIP descomprimido supera el tamaño máximo.")
        for info in sorted(miembros, key=lambda m: m.filename):
            ruta = None if info.is_dir() else _ruta_segura(info.filename)
            if ruta is None:
                continue
            tipo = _clasificar(inventario, ruta)
            if tipo == "otro":
                continue
            maximo = MAX_BYTES_PY if tipo == "python" else MAX_BYTES_NOTEBOOK
            if len(fuentes) >= MAX_ARCHIVOS_ANALIZADOS or leidos >= MAX_BYTES_ANALIZADOS:
                inventario.omitidos += 1
                continue
            try:
                crudo = _leer(zf, info, maximo + 1)
            except (zipfile.BadZipFile, OSError, RuntimeError, EOFError, ValueError):
                inventario.omitidos += 1
                continue
            leidos += len(crudo)
            if len(crudo) > maximo:
                inventario.omitidos += 1
                continue
            texto = crudo.decode("utf-8", errors="replace").replace("\x00", "")
            fuentes[ruta] = texto if tipo == "python" else codigo_de_notebook(texto)
    return fuentes, inventario


# ---------- Análisis ----------


def _recortar(texto: str) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= LIMITE_MENSAJE else texto[: LIMITE_MENSAJE - 1] + "…"


def _sintaxis(fuentes: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, ast.AST]]:
    """Errores de sintaxis por archivo y los árboles de los que sí se pudieron leer."""
    errores: list[dict[str, Any]] = []
    arboles: dict[str, ast.AST] = {}
    for ruta, texto in fuentes.items():
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                arboles[ruta] = ast.parse(texto, filename=ruta)
        except SyntaxError as error:
            linea = error.lineno or 0
            errores.append({"archivo": ruta, "linea": linea, "mensaje": _recortar(error.msg)})
        except (ValueError, RecursionError, MemoryError) as error:
            mensaje = f"No se pudo analizar ({type(error).__name__})."
            errores.append({"archivo": ruta, "linea": 0, "mensaje": mensaje})
    return errores, arboles


def _complejidad(fuentes: dict[str, str], arboles: dict[str, ast.AST]) -> dict[str, Any]:
    """Complejidad ciclomática (radon) de funciones y métodos de los archivos legibles."""
    bloques: list[dict[str, Any]] = []
    for ruta in arboles:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                visitados = cc_visit(fuentes[ruta])
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            continue
        for bloque in visitados:
            funciones = bloque.methods if isinstance(bloque, Class) else [bloque]
            for funcion in funciones:
                bloques.append(
                    {
                        "archivo": ruta,
                        "nombre": _recortar(funcion.fullname),
                        "linea": funcion.lineno,
                        "complejidad": funcion.complexity,
                    }
                )
    valores = [b["complejidad"] for b in bloques]
    complejas = sorted(bloques, key=lambda b: (-b["complejidad"], b["archivo"], b["linea"]))
    return {
        "funciones": len(valores),
        "promedio": round(sum(valores) / len(valores), 2) if valores else 0,
        "maxima": max(valores, default=0),
        "umbral_alta": UMBRAL_COMPLEJIDAD_ALTA,
        "alta": sum(1 for v in valores if v > UMBRAL_COMPLEJIDAD_ALTA),
        "mas_complejas": complejas[:MAX_ITEMS_DETALLE],
    }


def _es_archivo_test(ruta: str) -> bool:
    nombre = PurePosixPath(ruta).name.lower()
    return nombre.endswith(".py") and (nombre.startswith("test_") or nombre.endswith("_test.py"))


def _tests(
    arboles: dict[str, ast.AST], fuentes: dict[str, str], inventario: _Inventario
) -> dict[str, Any]:
    """Presencia de tests y número de funciones `test*` (no se ejecutan aquí)."""
    archivos = [ruta for ruta in fuentes if _es_archivo_test(ruta)]
    funciones = 0
    for ruta in archivos:
        arbol = arboles.get(ruta)
        if arbol is None:
            continue
        funciones += sum(
            1
            for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
            and nodo.name.startswith("test")
        )
    return {
        "tiene_tests": bool(archivos) or inventario.carpeta_tests,
        "archivos_test": len(archivos),
        "funciones_test": funciones,
        "ejecutados": False,
    }


def _ruff(fuentes: dict[str, str]) -> dict[str, Any]:
    """Hallazgos de ruff sobre una copia temporal de los `.py` (ruff solo lee, no ejecuta)."""
    if not fuentes:
        return {"disponible": True, "reglas": REGLAS_RUFF, "total": 0, "graves": 0,
                "por_codigo": {}, "hallazgos": []}  # fmt: skip
    with tempfile.TemporaryDirectory(prefix="rf06_") as carpeta:
        base = Path(carpeta).resolve()
        for ruta, texto in fuentes.items():
            relativo = ruta if ruta.lower().endswith(".py") else f"{ruta}.py"
            destino = (base / relativo).resolve()
            if not destino.is_relative_to(base):
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto, encoding="utf-8")
        comando = [
            sys.executable, "-m", "ruff", "check", "--isolated", "--no-cache", "--exit-zero",
            "--select", REGLAS_RUFF, "--output-format", "json", ".",
        ]  # fmt: skip
        entorno = {k: v for k, v in os.environ.items() if k.upper() in VARIABLES_ENTORNO_RUFF}
        try:
            proceso = subprocess.run(
                comando,
                cwd=base,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_RUFF_SEGUNDOS,
                env=entorno,
                check=False,
            )
            hallazgos = json.loads(proceso.stdout or "[]")
            if not isinstance(hallazgos, list):
                raise ValueError("Salida de ruff inesperada.")
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            logger.warning("ruff no se pudo ejecutar (%s).", type(error).__name__)
            return {"disponible": False, "reglas": REGLAS_RUFF}
        filas = [_fila_ruff(item, base) for item in hallazgos if isinstance(item, dict)]
    por_codigo = Counter(fila["codigo"] for fila in filas)
    filas.sort(key=lambda f: (f["archivo"], f["linea"]))
    return {
        "disponible": True,
        "reglas": REGLAS_RUFF,
        "total": len(filas),
        "graves": sum(1 for f in filas if _es_grave(f["codigo"])),
        "por_codigo": dict(por_codigo.most_common(MAX_ITEMS_DETALLE)),
        "hallazgos": filas[:MAX_ITEMS_DETALLE],
    }


def _fila_ruff(item: dict[str, Any], base: Path) -> dict[str, Any]:
    codigo = item.get("code") or "sintaxis"
    ubicacion = item.get("location") if isinstance(item.get("location"), dict) else {}
    try:
        archivo = Path(str(item.get("filename", ""))).resolve().relative_to(base).as_posix()
    except ValueError:
        archivo = ""
    return {
        "archivo": archivo,
        "linea": ubicacion.get("row") if isinstance(ubicacion.get("row"), int) else 0,
        "codigo": _recortar(codigo),
        "mensaje": _recortar(item.get("message", "")),
    }


def _es_grave(codigo: str) -> bool:
    """Sintaxis (sin código de regla, p. ej. `invalid-syntax`), E9xx o fallos claros de pyflakes."""
    es_regla = re.fullmatch(r"[A-Z]+[0-9]+", codigo) is not None
    return not es_regla or codigo.startswith("E9") or codigo in CODIGOS_GRAVES


# ---------- Punto de entrada ----------


def analizar_zip(datos: bytes) -> ResultadoEstatico:
    """Analiza el código del ZIP sin ejecutarlo. Lanza ValueError si el ZIP no se puede leer."""
    fuentes, inventario = _leer_fuentes(datos)
    errores, arboles = _sintaxis(fuentes)
    complejidad = _complejidad(fuentes, arboles)
    tests = _tests(arboles, fuentes, inventario)
    ruff = _ruff(fuentes)
    lineas = [linea for texto in fuentes.values() for linea in texto.splitlines()]
    resumen: dict[str, Any] = {
        "archivos_totales": inventario.archivos,
        "archivos_python": inventario.python,
        "archivos_notebook": inventario.notebooks,
        "archivos_otros_lenguajes": inventario.otros,
        "archivos_analizados": len(fuentes),
        "archivos_omitidos": inventario.omitidos,
        "lineas_totales": len(lineas),
        "lineas_codigo": sum(1 for x in lineas if x.strip() and not x.strip().startswith("#")),
        "archivos_con_error_sintaxis": len(errores),
        "funciones": complejidad["funciones"],
        "complejidad_promedio": complejidad["promedio"],
        "complejidad_maxima": complejidad["maxima"],
        "funciones_complejidad_alta": complejidad["alta"],
        "ruff_disponible": ruff["disponible"],
        "tiene_readme": inventario.readme,
        "tiene_requirements": inventario.requirements,
        "tiene_tests": tests["tiene_tests"],
        "archivos_test": tests["archivos_test"],
        "funciones_test": tests["funciones_test"],
    }
    if ruff["disponible"]:
        resumen["ruff_hallazgos"] = ruff["total"]
        resumen["ruff_graves"] = ruff["graves"]
    detalle = {
        "resumen": resumen,
        "sintaxis": {
            "archivos_analizados": len(fuentes),
            "con_error": len(errores),
            "errores": errores[:MAX_ITEMS_DETALLE],
        },
        "ruff": ruff,
        "complejidad": complejidad,
        "tests": tests,
    }
    return ResultadoEstatico(resumen=resumen, detalle=detalle)


def analizar_zip_seguro(datos: bytes) -> ResultadoEstatico | None:
    """Como `analizar_zip`, pero un fallo del análisis nunca tumba la evaluación (devuelve None)."""
    try:
        return analizar_zip(datos)
    except Exception as error:  # el análisis es complementario: nunca debe fallar la evaluación
        logger.warning("El análisis estático falló (%s).", type(error).__name__)
        return None
