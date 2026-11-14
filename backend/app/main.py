"""Punto de entrada de la API FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import laboratorios, rubricas, sandbox, usuarios, yo
from app.api.errores import registrar_manejadores
from app.config import Settings, get_settings

ORIGEN_LOCAL = "http://localhost:3000"


def origenes_permitidos(settings: Settings) -> list[str]:
    """Orígenes CORS: el dominio del frontend y localhost:3000 (nunca "*")."""
    origenes = [ORIGEN_LOCAL]
    frontend = settings.frontend_url.strip().rstrip("/")
    if frontend and frontend != "*" and frontend not in origenes:
        origenes.append(frontend)
    return origenes


def crear_app(settings: Settings | None = None) -> FastAPI:
    """Construye la aplicación con CORS restringido y sus rutas."""
    settings = settings or get_settings()
    aplicacion = FastAPI(title="Asesor Pedagógico Inteligente")
    aplicacion.add_middleware(
        CORSMiddleware,
        allow_origins=origenes_permitidos(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @aplicacion.get("/api/salud")
    def salud() -> dict[str, str]:
        """Estado del servicio (público)."""
        return {"estado": "ok"}

    registrar_manejadores(aplicacion)
    aplicacion.include_router(yo.router)
    aplicacion.include_router(usuarios.router)
    aplicacion.include_router(laboratorios.router)
    aplicacion.include_router(rubricas.router)
    aplicacion.include_router(sandbox.router)
    return aplicacion


app = crear_app()
