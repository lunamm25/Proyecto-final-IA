import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _zip_bytes(archivos: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for nombre, contenido in archivos.items():
            zf.writestr(nombre, contenido)
    return buffer.getvalue()


def test_endpoint_ejecuta_zip_valido():
    contenido = _zip_bytes({"main.py": "print('hola')"})
    respuesta = client.post(
        "/api/sandbox/ejecutar",
        files={"archivo": ("codigo.zip", contenido, "application/zip")},
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert "hola" in datos["stdout"]
    assert datos["codigo_salida"] == 0
    assert datos["error"] is None


def test_endpoint_rechaza_zip_slip():
    contenido = _zip_bytes({"../fuera.py": "print('x')"})
    respuesta = client.post(
        "/api/sandbox/ejecutar",
        files={"archivo": ("codigo.zip", contenido, "application/zip")},
    )
    assert respuesta.status_code == 200
    assert "zip-slip" in respuesta.json()["error"]


def test_endpoint_rechaza_archivo_no_zip():
    respuesta = client.post(
        "/api/sandbox/ejecutar",
        files={"archivo": ("nota.txt", b"hola", "text/plain")},
    )
    assert respuesta.json()["error"] == "El archivo debe ser un ZIP válido"
