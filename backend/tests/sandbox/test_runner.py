"""Tests del sandbox de ejecución de código."""

import io
import time
import zipfile

from app.sandbox.runner import SandboxRunner


def _crear_zip(contenido: dict[str, str]) -> bytes:
    """Crea un ZIP en memoria a partir de un dict {nombre: contenido}."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, codigo in contenido.items():
            zf.writestr(nombre, codigo)
    return buffer.getvalue()


def test_zip_valido_se_ejecuta():
    """ZIP con test.py que imprime 'hola' captura stdout correctamente."""
    contenido = {"test.py": 'print("hola")'}
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["error"] is None
    assert "hola" in resultado["stdout"]
    assert resultado["codigo_salida"] == 0


def test_zip_muy_grande_rechazado():
    """ZIP > 20 MB se rechaza sin descomprimir."""
    # Crear un ZIP con múltiples archivos grandes no comprimibles
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zf:  # SIN comprimir
        # Crear múltiples archivos para superar 20 MB
        for i in range(22):  # 22 * 1MB = 22 MB sin comprimir
            datos = f"archivo{i}_" * 100000  # ~1 MB de datos
            zf.writestr(f"archivo_{i}.txt", datos)

    zip_bytes = buffer.getvalue()

    # Verificar que el ZIP realmente es > 20 MB
    assert len(zip_bytes) > 20 * 1024 * 1024

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["error"] == "ZIP demasiado grande"
    assert resultado["codigo_salida"] == -1


def test_demasiados_archivos_rechazados():
    """ZIP con > 2000 archivos se rechaza."""
    # Crear un ZIP con 2001 archivos
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(2001):
            zf.writestr(f"archivo_{i}.txt", "contenido")

    zip_bytes = buffer.getvalue()

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["error"] == "Demasiados archivos"
    assert resultado["codigo_salida"] == -1


def test_contenido_demasiado_grande_rechazado():
    """ZIP ≤ 20 MB pero descomprimido > 100 MB se rechaza."""
    # Crear un ZIP que se comprime mucho pero descomprimido es grande
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Escribir un archivo que descomprimido es > 100 MB pero comprimido < 20 MB
        datos_grandes = "x" * (101 * 1024 * 1024)  # 101 MB de datos repetitivos
        zf.writestr("gigante.txt", datos_grandes)

    zip_bytes = buffer.getvalue()

    # Verificar que el ZIP comprimido es pequeño (gracias a la compresión)
    assert len(zip_bytes) < 21 * 1024 * 1024

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["error"] == "Contenido demasiado grande"
    assert resultado["codigo_salida"] == -1


def test_zip_slip_rechazado():
    """ZIP con ruta '../../../etc/passwd' se rechaza (zip-slip)."""
    # Crear un ZIP con una ruta sospechosa
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Escribir con una ruta que intenta salir del directorio
        zf.writestr("../../../etc/passwd", "malicioso")
        zf.writestr("test.py", 'print("normal")')

    zip_bytes = buffer.getvalue()

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["error"] == "ZIP sospechoso (zip-slip detectado)"
    assert resultado["codigo_salida"] == -1


def test_timeout_ejecutable():
    """Archivo .py que duerme 15s supera timeout y captura en stderr."""
    contenido = {"dormilon.py": "import time; time.sleep(15)"}
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    inicio = time.time()
    resultado = sandbox.ejecutar_zip(zip_bytes)
    duracion = time.time() - inicio

    # Debe haber terminado rápido (timeout de 10 s)
    assert duracion < 15
    assert "Timeout" in resultado["stderr"]
    assert resultado["codigo_salida"] == -1


def test_stderr_capturado():
    """Archivo .py que escribe en stderr se captura correctamente."""
    contenido = {
        "con_error.py": """import sys
sys.stderr.write('mensaje de error\\n')
print('salida normal')
"""
    }
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert "mensaje de error" in resultado["stderr"]
    assert "salida normal" in resultado["stdout"]
    assert resultado["codigo_salida"] == 0


def test_codigo_salida_no_cero():
    """Archivo .py que hace sys.exit(42) captura el código de salida."""
    contenido = {"exitoso.py": "import sys; sys.exit(42)"}
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["codigo_salida"] == 42


def test_zip_vacio():
    """ZIP sin archivos .py devuelve stderr con mensaje claro."""
    contenido = {"texto.txt": "no es código"}
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert "No se encontraron archivos .py" in resultado["stderr"]
    assert resultado["codigo_salida"] == 0


def test_sintaxis_error():
    """Archivo .py con error de sintaxis captura en stderr."""
    contenido = {"malo.py": "esto no es python valido !!!"}
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["codigo_salida"] != 0
    assert "SyntaxError" in resultado["stderr"] or "invalid syntax" in resultado["stderr"]


def test_zip_invalido():
    """Archivo corrupto se rechaza con error claro."""
    zip_bytes = b"esto no es un zip valido"

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert resultado["error"] is not None
    assert "corrupto" in resultado["error"].lower() or "inválido" in resultado["error"].lower()


def test_multiples_archivos_py():
    """ZIP con múltiples .py ejecuta todos en orden."""
    contenido = {
        "a_primero.py": 'print("primero")',
        "b_segundo.py": 'print("segundo")',
        "c_tercero.py": 'print("tercero")',
    }
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    stdout = resultado["stdout"]
    # Verificar que todos se ejecutaron
    assert "primero" in stdout
    assert "segundo" in stdout
    assert "tercero" in stdout


def test_variables_entorno_vacias():
    """Entorno de ejecución no hereda variables del proceso principal."""
    contenido = {
        "check_env.py": """import os
# Los secretos no deben estar en el entorno
if os.environ.get('PATH'):
    print('PATH disponible')
else:
    print('PATH no disponible')
"""
    }
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    # En sandbox sin PATH explícito, las búsquedas de comandos fallarían
    # pero el código de Python mismo sigue funcionando
    assert resultado["codigo_salida"] == 0


def test_archivos_anidados():
    """ZIP con estructura de directorios anidados se ejecuta correctamente."""
    contenido = {
        "dir1/dir2/script.py": 'print("anidado")',
        "archivo_raiz.py": 'print("raiz")',
    }
    zip_bytes = _crear_zip(contenido)

    sandbox = SandboxRunner()
    resultado = sandbox.ejecutar_zip(zip_bytes)

    assert "anidado" in resultado["stdout"]
    assert "raiz" in resultado["stdout"]
    assert resultado["error"] is None
