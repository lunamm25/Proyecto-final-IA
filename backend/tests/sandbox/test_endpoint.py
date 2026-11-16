import io
import zipfile

import pytest

from app.main import crear_app
from tests.test_auth import (
    ID_ADMIN,
    ID_DOCENTE,
    ID_ESTUDIANTE,
    ajustes,
    con_token,
    preparar,
    token_hs,
)

RUTA = "/api/sandbox/ejecutar"
DOCENTE = con_token(token_hs(ID_DOCENTE))


@pytest.fixture
def client(fabrica_api):
    """Cliente con el sandbox habilitado y perfiles de cada rol (el endpoint exige docente)."""
    config = ajustes(sandbox_habilitado=True)
    return preparar(crear_app(config), fabrica_api, config)


def _zip_bytes(archivos: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for nombre, contenido in archivos.items():
            zf.writestr(nombre, contenido)
    return buffer.getvalue()


def test_endpoint_ejecuta_zip_valido(client):
    contenido = _zip_bytes({"main.py": "print('hola')"})
    respuesta = client.post(
        RUTA,
        files={"archivo": ("codigo.zip", contenido, "application/zip")},
        headers=DOCENTE,
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert "hola" in datos["stdout"]
    assert datos["codigo_salida"] == 0
    assert datos["error"] is None


def test_endpoint_rechaza_zip_slip(client):
    contenido = _zip_bytes({"../fuera.py": "print('x')"})
    respuesta = client.post(
        RUTA,
        files={"archivo": ("codigo.zip", contenido, "application/zip")},
        headers=DOCENTE,
    )
    assert respuesta.status_code == 200
    assert "zip-slip" in respuesta.json()["error"]


def test_endpoint_rechaza_archivo_no_zip(client):
    respuesta = client.post(
        RUTA,
        files={"archivo": ("nota.txt", b"hola", "text/plain")},
        headers=DOCENTE,
    )
    assert respuesta.json()["error"] == "El archivo debe ser un ZIP válido"


def _enviar(client, headers=None):
    contenido = _zip_bytes({"main.py": "print('hola')"})
    return client.post(
        RUTA,
        files={"archivo": ("codigo.zip", contenido, "application/zip")},
        headers=headers or {},
    )


def test_endpoint_sin_token_responde_401(client):
    respuesta = _enviar(client)
    assert respuesta.status_code == 401
    assert respuesta.headers.get("www-authenticate") == "Bearer"


def test_endpoint_estudiante_responde_403_y_no_ejecuta(client):
    respuesta = _enviar(client, con_token(token_hs(ID_ESTUDIANTE)))
    assert respuesta.status_code == 403
    assert "stdout" not in respuesta.json()


def test_endpoint_admin_puede_ejecutar(client):
    respuesta = _enviar(client, con_token(token_hs(ID_ADMIN)))
    assert respuesta.status_code == 200
    assert "hola" in respuesta.json()["stdout"]


def test_endpoint_apagado_por_defecto_responde_404(cliente_api):
    """Sin SANDBOX_HABILITADO el endpoint no existe, ni siquiera para un docente."""
    respuesta = _enviar(cliente_api, DOCENTE)
    assert respuesta.status_code == 404
    assert "stdout" not in respuesta.json()


def test_endpoint_apagado_responde_404_sin_token(cliente_api):
    """Apagado tampoco revela que existe: 404 y no 401."""
    assert _enviar(cliente_api).status_code == 404


def test_sandbox_habilitado_es_false_por_defecto():
    from app.config import Settings

    assert Settings(_env_file=None).sandbox_habilitado is False
