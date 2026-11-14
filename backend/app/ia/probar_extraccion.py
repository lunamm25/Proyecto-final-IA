"""Prueba manual de extracción de rúbricas: `python -m app.ia.probar_extraccion <ruta>`."""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.ia.providers import ErrorConfiguracionLLM, ErrorRespuestaLLM, obtener_proveedor
from app.ia.rubricas import (
    VERSION_PROMPT_EXTRAER_RUBRICA,
    extraer_rubrica,
    extraer_texto_documento,
)

RUTA_ENV = Path(__file__).resolve().parents[2] / ".env"


def main() -> int:
    """Extrae la rúbrica del archivo indicado con el proveedor configurado y la muestra."""
    if len(sys.argv) != 2:
        print("Uso: python -m app.ia.probar_extraccion <ruta_rubrica>", file=sys.stderr)
        return 2
    load_dotenv(RUTA_ENV)
    try:
        texto = extraer_texto_documento(sys.argv[1])
        proveedor = obtener_proveedor()
        print(f"Proveedor: {proveedor.nombre}")
        print(f"Modelo: {proveedor.modelo}")
        print(f"Versión de prompt: {VERSION_PROMPT_EXTRAER_RUBRICA}")
        print(f"Caracteres de texto enviados: {len(texto)}")
        rubrica = extraer_rubrica(texto, proveedor)
    except (ValueError, ErrorConfiguracionLLM, ErrorRespuestaLLM) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(rubrica.model_dump(), indent=2, ensure_ascii=False))
    suma = sum(c.ponderacion for c in rubrica.criterios)
    print(f"Suma de ponderaciones (informativo): {suma}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
