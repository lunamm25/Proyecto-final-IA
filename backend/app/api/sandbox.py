"""Endpoint para ejecutar código en sandbox."""

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from app.sandbox.runner import SandboxRunner

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


class EjecucionResponse(BaseModel):
    """Respuesta de la ejecución del sandbox."""

    stdout: str
    stderr: str
    codigo_salida: int
    error: str | None = None


@router.post("/ejecutar", response_model=EjecucionResponse)
async def ejecutar_codigo(archivo: UploadFile = File(...)) -> EjecucionResponse:  # noqa: B008
    """Ejecuta código Python dentro de un ZIP con límites de seguridad.

    Recibe un archivo ZIP, lo valida y ejecuta el código dentro.
    """
    # Validar que es un ZIP
    if archivo.content_type not in ["application/zip", "application/x-zip-compressed"]:
        return EjecucionResponse(
            stdout="",
            stderr="",
            codigo_salida=-1,
            error="El archivo debe ser un ZIP válido",
        )

    # Leer contenido del archivo
    contenido = await archivo.read()

    # Ejecutar en sandbox
    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(contenido)

    return EjecucionResponse(**resultado)
