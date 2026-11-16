"""Extracción de rúbricas: texto del documento -> RubricaSchema mediante el LLM (RF-03 CA1).

Los puntajes de los niveles los decide el código, no el LLM: se conservan solo si aparecen en
el documento; si no, con 3 niveles se asignan 5.0 / 3.5 / 0.0 de mayor a menor desempeño.
"""

import io
import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from app.ia.providers import LLMProvider
from app.ia.schemas import Criterio, RubricaSchema

CARPETA_PROMPTS = Path(__file__).resolve().parent / "prompts"
EXTENSIONES_TEXTO = {".md", ".txt"}
MARCADOR_TEXTO = "{texto_rubrica}"
SEPARADOR_ENCABEZADO = "---"

# Puntajes que asigna el código, de mayor a menor desempeño, cuando el documento no los trae.
PUNTAJES_TRES_NIVELES = (5.0, 3.5, 0.0)
# Acotado y anclado: evita el retroceso cuadrático con cadenas largas de dígitos (ReDoS).
_NUMERO = r"(?<![\d.,])\d{1,6}(?:[.,]\d{1,4})?(?!\d)"
_RE_NUMERO = re.compile(_NUMERO)
_RE_RANGO = re.compile(rf"({_NUMERO})\s*(?:[-–—]|a)\s*({_NUMERO})")
_CENTESIMA = Decimal("0.01")

# Encabezados y pies de página: la línea con "Página N" y sus vecinas, repetidas en ≥3 páginas.
_RE_MARCA_PAGINA = re.compile(r"\b(?:p[aá]gina|page|p[aá]g\.?)\s*\d+", re.IGNORECASE)
MIN_REPETICIONES_PAGINA = 3


def cargar_prompt(nombre: str) -> tuple[str, str]:
    """Lee prompts/<nombre>.md y devuelve (versión, cuerpo).

    El archivo empieza con 'version: x.y'. Si las líneas que siguen sin línea en blanco
    terminan en '---', son metadatos (p. ej. el historial de cambios) y no se envían al modelo.
    Un '---' más abajo, dentro del cuerpo, se conserva.
    """
    ruta = CARPETA_PROMPTS / f"{nombre}.md"
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el prompt '{nombre}' en {CARPETA_PROMPTS}.")
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    primera = lineas[0].strip() if lineas else ""
    if not primera.lower().startswith("version:"):
        raise ValueError(f"El prompt '{nombre}' debe empezar con la línea 'version: x.y'.")
    version = primera.split(":", 1)[1].strip()
    resto = lineas[1:]
    for indice, linea in enumerate(resto):
        if not linea.strip():
            break
        if linea.strip() == SEPARADOR_ENCABEZADO:
            resto = resto[indice + 1 :]
            break
    while resto and not resto[0].strip():
        resto = resto[1:]
    return version, "\n".join(resto).strip() + "\n"


VERSION_PROMPT_EXTRAER_RUBRICA, _PLANTILLA_EXTRAER_RUBRICA = cargar_prompt("extraer_rubrica")


def construir_prompt_rubrica(texto: str) -> str:
    """Inserta el texto de la rúbrica en la plantilla del prompt."""
    return _PLANTILLA_EXTRAER_RUBRICA.replace(MARCADOR_TEXTO, texto.strip())


def _clave_linea(linea: str) -> str:
    """Línea sin espacios repetidos y con los números reemplazados (para comparar páginas)."""
    return re.sub(r"\d+", "#", " ".join(linea.split()))


def quitar_encabezados_pagina(texto: str) -> str:
    """Quita los encabezados/pies que se repiten en cada página para que no tapen el título.

    Se quita la línea con "Página N" y sus vecinas inmediatas cuando se repiten en al menos 3
    páginas; así no se borran encabezados de tabla ni frases que se repiten una o dos veces.
    """
    lineas = texto.splitlines()
    claves = [_clave_linea(linea) for linea in lineas]
    conteo = Counter(claves)
    marcas = {
        i
        for i, linea in enumerate(lineas)
        if _RE_MARCA_PAGINA.search(linea) and conteo[claves[i]] >= MIN_REPETICIONES_PAGINA
    }
    vecinas = {
        j
        for i in marcas
        for j in (i - 1, i + 1)
        if 0 <= j < len(lineas) and claves[j] and conteo[claves[j]] >= MIN_REPETICIONES_PAGINA
    }
    quitar = marcas | vecinas
    return "\n".join(linea for i, linea in enumerate(lineas) if i not in quitar).strip()


def _a_decimal(texto: str) -> Decimal | None:
    """Convierte '4,5' o '4.5' en Decimal redondeado a centésimas (None si no es número)."""
    try:
        return Decimal(texto.replace(",", ".")).quantize(_CENTESIMA, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def numeros_del_documento(texto: str) -> set[Decimal]:
    """Números de un fragmento más el punto medio de cada rango ('4.5-5.0' -> 4.75)."""
    numeros = {d for n in _RE_NUMERO.findall(texto) if (d := _a_decimal(n)) is not None}
    for minimo, maximo in _RE_RANGO.findall(texto):
        a, b = _a_decimal(minimo), _a_decimal(maximo)
        if a is not None and b is not None:
            numeros.add(((a + b) / 2).quantize(_CENTESIMA, rounding=ROUND_HALF_UP))
    return numeros


def _numeros_del_nivel(nombre: str, lineas: list[str]) -> set[Decimal]:
    """Números de las líneas que nombran el nivel y de la siguiente ('Excelente (4.5-5.0)')."""
    clave = " ".join(nombre.split()).casefold()
    numeros: set[Decimal] = set()
    if not clave:
        return numeros
    for indice, linea in enumerate(lineas):
        if clave in linea:
            numeros |= numeros_del_documento("\n".join(lineas[indice : indice + 2]))
    return numeros


def _puntajes_del_documento(criterio: Criterio, lineas: list[str]) -> bool:
    """True si cada puntaje aparece junto al nombre de su nivel y todos son distintos."""
    puntajes = [_a_decimal(str(n.puntaje)) for n in criterio.niveles]
    junto_al_nombre = all(
        p in _numeros_del_nivel(n.nombre, lineas)
        for n, p in zip(criterio.niveles, puntajes, strict=True)
    )
    return len(set(puntajes)) == len(puntajes) and junto_al_nombre


def asignar_puntajes(rubrica: RubricaSchema, texto: str) -> RubricaSchema:
    """Conserva los puntajes que están en el documento; si no, 3 niveles -> 5.0 / 3.5 / 0.0.

    Con otra cantidad de niveles no se inventan puntajes: queda lo que devolvió el modelo y el
    validador del backend reporta la inconsistencia (RF-03 CA2). Un puntaje solo cuenta como del
    documento si aparece en la línea que nombra su nivel o en la siguiente: un número suelto en
    otra parte (minutos, numeración de secciones) no basta.
    """
    lineas = [" ".join(linea.split()).casefold() for linea in texto.splitlines()]
    criterios = []
    for criterio in rubrica.criterios:
        sin_puntajes = not _puntajes_del_documento(criterio, lineas)
        if sin_puntajes and len(criterio.niveles) == len(PUNTAJES_TRES_NIVELES):
            niveles = [
                nivel.model_copy(update={"puntaje": puntaje})
                for nivel, puntaje in zip(criterio.niveles, PUNTAJES_TRES_NIVELES, strict=True)
            ]
            criterio = criterio.model_copy(update={"niveles": niveles})
        criterios.append(criterio)
    return rubrica.model_copy(update={"criterios": criterios})


def extraer_rubrica(texto: str, proveedor: LLMProvider) -> RubricaSchema:
    """Convierte el texto de una rúbrica en un RubricaSchema validado."""
    if not texto or not texto.strip():
        raise ValueError("El texto de la rúbrica está vacío; no hay nada que extraer.")
    limpio = quitar_encabezados_pagina(texto) or texto.strip()
    rubrica = proveedor.generar_json(construir_prompt_rubrica(limpio), RubricaSchema)
    return asignar_puntajes(rubrica, limpio)


def _texto_docx(datos: bytes) -> str:
    """Extrae párrafos y tablas de un .docx respetando el orden del documento."""
    try:
        import docx
        from docx.table import Table
    except ImportError as error:
        raise ValueError("Falta la librería python-docx (pip install python-docx).") from error
    try:
        documento = docx.Document(io.BytesIO(datos))
    except Exception as error:  # archivo dañado o que no es .docx
        raise ValueError(f"No se pudo leer el archivo .docx: {error}") from error
    lineas: list[str] = []
    for bloque in documento.iter_inner_content():
        if isinstance(bloque, Table):
            lineas.extend(_filas_tabla(bloque))
            lineas.append("")
        elif bloque.text.strip():
            lineas.append(bloque.text.strip())
    return "\n".join(lineas).strip()


def _texto_pdf(datos: bytes) -> str:
    """Extrae el texto de todas las páginas de un PDF, en orden, una página tras otra.

    Se usa el modo de extracción por defecto de pypdf ("plain"): con las rúbricas reales
    conserva cada criterio junto a su peso; el modo "layout" partía los nombres largos
    alrededor de la columna de puntos y agregaba muchos espacios y líneas vacías.
    """
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ValueError("Falta la librería pypdf (pip install pypdf).") from error
    try:
        lector = PdfReader(io.BytesIO(datos))
        paginas = [(pagina.extract_text() or "").strip() for pagina in lector.pages]
    except Exception as error:  # PDF dañado, cifrado o que no es PDF
        raise ValueError(f"No se pudo leer el archivo PDF: {error}") from error
    texto = "\n".join(p for p in paginas if p).strip()
    if not texto:
        raise ValueError(
            "El PDF no tiene texto extraíble (parece escaneado o solo con imágenes); "
            "sube la rúbrica en .docx, .md, .txt o un PDF con texto."
        )
    return texto


def _filas_tabla(tabla) -> list[str]:
    """Convierte cada fila de una tabla en una línea con celdas separadas por ' | '."""
    filas: list[str] = []
    for fila in tabla.rows:
        celdas: list[str] = []
        vistas: set[int] = set()
        for celda in fila.cells:
            if id(celda._tc) in vistas:  # celdas combinadas se repiten en python-docx
                continue
            vistas.add(id(celda._tc))
            celdas.append(" ".join(celda.text.split()))
        if any(celdas):
            filas.append(" | ".join(celdas))
    return filas


def extraer_texto_documento(origen: str | Path | bytes, nombre: str | None = None) -> str:
    """Extrae el texto de una rúbrica en .md, .txt, .docx o .pdf (ruta, o bytes + nombre)."""
    if isinstance(origen, bytes):
        if not nombre:
            raise ValueError("Si se envían bytes, hay que indicar el nombre del archivo.")
        datos = origen
    else:
        ruta = Path(origen)
        if not ruta.is_file():
            raise ValueError(f"No existe el archivo: {ruta}")
        datos = ruta.read_bytes()
        nombre = nombre or ruta.name
    extension = Path(nombre).suffix.lower()
    if extension in EXTENSIONES_TEXTO:
        try:
            return datos.decode("utf-8-sig").strip()
        except UnicodeDecodeError as error:
            raise ValueError(f"El archivo '{nombre}' no está codificado en UTF-8.") from error
    if extension == ".docx":
        return _texto_docx(datos)
    if extension == ".pdf":
        return _texto_pdf(datos)
    raise ValueError(f"Formato '{extension or nombre}' no soportado; usa .pdf, .docx, .md o .txt.")
