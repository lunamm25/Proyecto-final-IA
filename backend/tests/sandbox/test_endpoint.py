import io
import zipfile

import pytest

from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE, con_token, token_hs

RUTA = "/api/sandbox/ejecutar"
DOCENTE = con_token(token_hs(ID_DOCENTE))


@pytest.fixture
def client(cliente_api):
    """Cliente con BD de prueba y perfiles de cada rol (el endpoint exige rol docente)."""
    return cliente_api


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
