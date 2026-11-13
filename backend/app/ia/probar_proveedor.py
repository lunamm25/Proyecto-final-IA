"""Prueba manual del proveedor de IA: `cd backend && python -m app.ia.probar_proveedor`."""

import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from app.ia.providers import ErrorConfiguracionLLM, ErrorRespuestaLLM, obtener_proveedor

RUTA_ENV = Path(__file__).resolve().parents[2] / ".env"


class RespuestaPrueba(BaseModel):
    """Esquema mínimo para comprobar la salida JSON del proveedor."""

    respuesta: str
    confianza: float


def main() -> int:
    """Envía una pregunta simple al proveedor configurado y muestra el resultado."""
    load_dotenv(RUTA_ENV)
    try:
        proveedor = obtener_proveedor()
        print(f"Proveedor: {proveedor.nombre}")
        print(f"Modelo: {proveedor.modelo}")
        print(f"Temperatura: {proveedor.temperatura}")
        resultado = proveedor.generar_json(
            "Responde en español: ¿qué es una rúbrica de evaluación? Usa una sola frase. "
            "Incluye 'confianza' entre 0 y 1.",
            RespuestaPrueba,
        )
    except (ErrorConfiguracionLLM, ErrorRespuestaLLM) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(resultado.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
