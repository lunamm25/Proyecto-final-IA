"""Extracción de rúbricas: texto del documento -> RubricaSchema mediante el LLM (RF-03 CA1)."""

import io
from pathlib import Path

from app.ia.providers import LLMProvider
from app.ia.schemas import RubricaSchema

CARPETA_PROMPTS = Path(__file__).resolve().parent / "prompts"
EXTENSIONES_TEXTO = {".md", ".txt"}
MARCADOR_TEXTO = "{texto_rubrica}"


def cargar_prompt(nombre: str) -> tuple[str, str]:
    """Lee prompts/<nombre>.md y devuelve (versión, cuerpo)."""
    ruta = CARPETA_PROMPTS / f"{nombre}.md"
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el prompt '{nombre}' en {CARPETA_PROMPTS}.")
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    primera = lineas[0].strip() if lineas else ""
    if not primera.lower().startswith("version:"):
        raise ValueError(f"El prompt '{nombre}' debe empezar con la línea 'version: x.y'.")
    version = primera.split(":", 1)[1].strip()
    resto = lineas[1:]
    while resto and resto[0].strip() in ("", "---"):
        resto = resto[1:]
    return version, "\n".join(resto).strip() + "\n"


VERSION_PROMPT_EXTRAER_RUBRICA, _PLANTILLA_EXTRAER_RUBRICA = cargar_prompt("extraer_rubrica")


def construir_prompt_rubrica(texto: str) -> str:
    """Inserta el texto de la rúbrica en la plantilla del prompt."""
    return _PLANTILLA_EXTRAER_RUBRICA.replace(MARCADOR_TEXTO, texto.strip())


def extraer_rubrica(texto: str, proveedor: LLMProvider) -> RubricaSchema:
    """Convierte el texto de una rúbrica en un RubricaSchema validado."""
    if not texto or not texto.strip():
        raise ValueError("El texto de la rúbrica está vacío; no hay nada que extraer.")
    return proveedor.generar_json(construir_prompt_rubrica(texto), RubricaSchema)


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
