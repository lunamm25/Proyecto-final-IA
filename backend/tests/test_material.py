"""Pruebas del material real de la evaluación (RF-05): PDF y ZIP desde el almacén, saneado,
truncado, protección zip-slip/zip-bomb y verificación técnica opcional.

Nunca se usa la red, el `.env` ni el SandboxRunner real: el almacén y el ejecutor son dobles.
"""

import json

import httpx
import pytest
from sqlalchemy import select

from app.api.deps import (
    obtener_almacen,
    obtener_cargador_material,
    obtener_ejecutor_codigo,
)
from app.config import get_settings
from app.models import Auditoria, Entrega, Evaluacion, Perfil, VerificacionCodigo
from app.services import material
from app.services.material import (
    ZipInseguroError,
    extraer_codigo_zip,
    extraer_texto_pdf,
    obtener_material,
    resumen_verificacion,
    sanear_texto,
)
from tests.dobles_entregas import AlmacenMemoria, pdf_con_texto, zip_con
from tests.test_auth import ID_DOCENTE, ID_ESTUDIANTE, ajustes
from tests.test_evaluaciones import auth, evaluar, leer, poner_estado

MARCADOR_SALIDA = "MARCADOR_STDOUT_NO_DEBE_SALIR"
MARCADOR_ERROR = "MARCADOR_STDERR_NO_DEBE_SALIR"
CORREO = "ana.estudiante@uni.edu.co"


@pytest.fixture(autouse=True)
def sin_red_httpx(monkeypatch):
    """Falla si algún test intenta una conexión HTTP real."""

    def _prohibido(*_args, **_kwargs):
        raise AssertionError("No se permite usar la red en los tests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _prohibido)


class EjecutorFalso:
    """Sustituye a SandboxRunner.ejecutar_zip: cuenta llamadas y devuelve salida con marcadores."""

    def __init__(self, resultado: dict | None = None, excepcion: Exception | None = None) -> None:
        self.llamadas: list[bytes] = []
        self.excepcion = excepcion
        self.resultado = resultado or {
            "stdout": MARCADOR_SALIDA,
            "stderr": MARCADOR_ERROR,
            "codigo_salida": 0,
            "error": None,
        }

    def __call__(self, datos: bytes) -> dict:
        self.llamadas.append(datos)
        if self.excepcion is not None:
            raise self.excepcion
        return self.resultado


# ---------- Extracción del PDF ----------


def test_extrae_texto_del_pdf():
    texto = extraer_texto_pdf(pdf_con_texto("Hola mundo", "Segunda linea"))
    assert "Hola mundo" in texto
    assert "Segunda linea" in texto


def test_pdf_ilegible_lanza_error():
    with pytest.raises(material.MaterialIlegibleError):
        extraer_texto_pdf(b"%PDF-1.4 basura")


# ---------- Extracción del código del ZIP ----------


def test_extrae_solo_los_py_con_encabezado_por_archivo():
    datos = zip_con(
        {
            "src/main.py": "def suma(a, b):\n    return a + b\n",
            "README.md": "no es python",
            "tests/test_main.py": "def test_suma():\n    assert True\n",
            "datos.bin": b"\x00\x01",
        }
    )
    codigo = extraer_codigo_zip(datos)
    assert "### Archivo: src/main.py" in codigo
    assert "### Archivo: tests/test_main.py" in codigo
    assert "def suma(a, b):" in codigo
    assert "README" not in codigo and "no es python" not in codigo
    assert codigo.index("src/main.py") < codigo.index("tests/test_main.py")


def test_zip_slip_se_ignora():
    datos = zip_con(
        {
            "../../fuera.py": "MALICIOSO_RELATIVO = 1",
            "/etc/absoluto.py": "MALICIOSO_ABSOLUTO = 1",
            "C:/windows/x.py": "MALICIOSO_UNIDAD = 1",
            "a/../../b.py": "MALICIOSO_MEDIO = 1",
            "ok.py": "BUENO = 1",
        }
    )
    codigo = extraer_codigo_zip(datos)
    assert "BUENO = 1" in codigo
    assert "MALICIOSO" not in codigo


def test_zip_con_demasiados_archivos_se_rechaza(monkeypatch):
    monkeypatch.setattr(material, "MAX_ARCHIVOS_ZIP", 3)
    with pytest.raises(ZipInseguroError):
        extraer_codigo_zip(zip_con({f"a{i}.py": "x = 1" for i in range(5)}))


def test_zip_bomba_se_rechaza_por_tamano_declarado(monkeypatch):
    monkeypatch.setattr(material, "MAX_DESCOMPRIMIDO_BYTES", 1000)
    with pytest.raises(ZipInseguroError):
        extraer_codigo_zip(zip_con({"bomba.py": "0" * 50_000}))


def test_zip_lectura_real_limitada(monkeypatch):
    # Aunque el tamaño declarado pase, la lectura real se corta en el límite.
    monkeypatch.setattr(material, "MAX_DESCOMPRIMIDO_BYTES", 10**9)
    monkeypatch.setattr(material, "LIMITE_CODIGO", 500)
    codigo = extraer_codigo_zip(zip_con({"grande.py": "x = 1\n" * 100_000}))
    assert len(codigo) <= 500


def test_zip_invalido_lanza_error():
    with pytest.raises(material.MaterialIlegibleError):
        extraer_codigo_zip(b"PK\x03\x04 no es zip")


def test_codigo_truncado_lo_anota(monkeypatch):
    monkeypatch.setattr(material, "LIMITE_CODIGO", 300)
    codigo = extraer_codigo_zip(zip_con({f"m{i}.py": "y = 2\n" * 40 for i in range(5)}))
    assert len(codigo) <= 300
    assert "truncado" in codigo


def test_carpetas_de_entorno_se_ignoran():
    codigo = extraer_codigo_zip(
        zip_con(
            {
                ".venv/lib/x.py": "ENTORNO = 1",
                "venv/y.py": "ENTORNO = 2",
                "__MACOSX/._a.py": "ENTORNO = 3",
                "app.py": "APP = 1",
            }
        )
    )
    assert "APP = 1" in codigo and "ENTORNO" not in codigo


# ---------- Saneamiento ----------


def test_quita_correos_y_nombre_del_estudiante():
    texto = (
        f"Autora: Ana Estudiante ({CORREO}). Contacto del profe: profe@uni.edu.co. "
        "ANA ESTUDIANTE presenta el informe."
    )
    limpio = sanear_texto(texto, "Ana Estudiante", CORREO)
    assert "Ana Estudiante" not in limpio and "ANA ESTUDIANTE" not in limpio
    assert CORREO not in limpio and "profe@uni.edu.co" not in limpio
    assert "[estudiante]" in limpio and "[correo]" in limpio


def test_sanear_sin_nombre_ni_correo():
    assert sanear_texto("x@y.co hola", None, None) == "[correo] hola"


# ---------- obtener_material con almacén y ejecutor dobles ----------


def preparar_entrega(fabrica, almacen, *, pdf=True, zip_=True, informe_extra="") -> Entrega:
    with fabrica() as s:
        perfil = s.get(Perfil, ID_ESTUDIANTE)
        perfil.correo = CORREO
        entrega = s.get(Entrega, 1)
        entrega.pdf_path = f"{ID_ESTUDIANTE}/1/informe.pdf" if pdf else None
        entrega.codigo_zip_path = f"{ID_ESTUDIANTE}/1/codigo.zip" if zip_ else None
        s.commit()
        if pdf:
            almacen.objetos[entrega.pdf_path] = pdf_con_texto(
                "Informe de Ana Estudiante sobre funciones.",
                f"Correo: {CORREO}",
                informe_extra,
            )
        if zip_:
            almacen.objetos[entrega.codigo_zip_path] = zip_con(
                {"main.py": f"# autora: {CORREO}\ndef suma(a, b):\n    return a + b\n"}
            )
        s.expunge(entrega)
        return entrega


def test_material_real_con_pdf_y_zip(datos):
    almacen = AlmacenMemoria()
    entrega = preparar_entrega(datos, almacen)
    ejecutor = EjecutorFalso()
    with datos() as s:
        resultado = obtener_material(
            s, entrega, almacen=almacen, verificacion_activa=False, ejecutar=ejecutor
        )
    assert "sobre funciones" in resultado.texto_informe
    assert "def suma(a, b):" in (resultado.resumen_codigo or "")
    todo = resultado.texto_informe + (resultado.resumen_codigo or "")
    assert CORREO not in todo and "Ana Estudiante" not in todo
    assert resultado.resultados_verificacion is None
    assert ejecutor.llamadas == []


def test_material_verificacion_activa_solo_tres_campos(datos):
    almacen = AlmacenMemoria()
    entrega = preparar_entrega(datos, almacen)
    ejecutor = EjecutorFalso()
    with datos() as s:
        resultado = obtener_material(
            s, entrega, almacen=almacen, verificacion_activa=True, ejecutar=ejecutor
        )
    assert len(ejecutor.llamadas) == 1
    assert resultado.resultados_verificacion == {
        "codigo_salida": 0,
        "tiene_error": False,
        "ejecucion_exitosa": True,
    }
    assert MARCADOR_SALIDA not in repr(resultado) and MARCADOR_ERROR not in repr(resultado)


@pytest.mark.parametrize(
    ("salida", "esperado"),
    [
        (
            {"stdout": "", "stderr": "x", "codigo_salida": 1, "error": None},
            {"codigo_salida": 1, "tiene_error": False, "ejecucion_exitosa": False},
        ),
        (
            {"stdout": "", "stderr": "", "codigo_salida": -1, "error": "ZIP demasiado grande"},
            {"codigo_salida": -1, "tiene_error": True, "ejecucion_exitosa": False},
        ),
        (
            {"codigo_salida": "raro"},
            {"codigo_salida": -1, "tiene_error": True, "ejecucion_exitosa": False},
        ),
    ],
)
def test_resumen_de_la_ejecucion(datos, salida, esperado):
    almacen = AlmacenMemoria()
    entrega = preparar_entrega(datos, almacen)
    with datos() as s:
        resultado = obtener_material(
            s, entrega, almacen=almacen, verificacion_activa=True, ejecutar=EjecutorFalso(salida)
        )
    assert resultado.resultados_verificacion == esperado


def test_ejecutor_que_lanza_queda_como_error(datos):
    almacen = AlmacenMemoria()
    entrega = preparar_entrega(datos, almacen)
    ejecutor = EjecutorFalso(excepcion=RuntimeError(MARCADOR_ERROR))
    with datos() as s:
        resultado = obtener_material(
            s, entrega, almacen=almacen, verificacion_activa=True, ejecutar=ejecutor
        )
    assert resultado.resultados_verificacion == {
        "codigo_salida": -1,
        "tiene_error": True,
        "ejecucion_exitosa": False,
    }


def test_sin_zip_no_se_ejecuta_nada(datos):
    almacen = AlmacenMemoria()
    entrega = preparar_entrega(datos, almacen, zip_=False)
    ejecutor = EjecutorFalso()
    with datos() as s:
        resultado = obtener_material(
            s, entrega, almacen=almacen, verificacion_activa=True, ejecutar=ejecutor
        )
    assert ejecutor.llamadas == []
    assert resultado.resumen_codigo is None
    assert resultado.resultados_verificacion is None


def test_informe_truncado_lo_anota(datos, monkeypatch):
    monkeypatch.setattr(material, "LIMITE_INFORME", 200)
    almacen = AlmacenMemoria()
    entrega = preparar_entrega(datos, almacen, zip_=False, informe_extra="z" * 400)
    with datos() as s:
        resultado = obtener_material(
            s, entrega, almacen=almacen, verificacion_activa=False, ejecutar=EjecutorFalso()
        )
    assert len(resultado.texto_informe) <= 200
    assert "truncado" in resultado.texto_informe


def test_resumen_verificacion_filtra_campos():
    assert resumen_verificacion(None) is None
    assert resumen_verificacion({"stdout": "x"}) is None
    assert resumen_verificacion(
        {"codigo_salida": 0, "tiene_error": False, "ejecucion_exitosa": True, "stdout": "x"}
    ) == {"codigo_salida": 0, "tiene_error": False, "ejecucion_exitosa": True}


# ---------- Evaluación de punta a punta con el material real ----------


@pytest.fixture
def con_material_real(cliente, datos):
    """Quita el material falso: usa obtener_material con un almacén en memoria."""
    almacen = AlmacenMemoria()
    ejecutor = EjecutorFalso()
    del cliente.app.dependency_overrides[obtener_cargador_material]
    cliente.app.dependency_overrides[obtener_almacen] = lambda: almacen
    cliente.app.dependency_overrides[obtener_ejecutor_codigo] = lambda: ejecutor
    return cliente, almacen, ejecutor


def activar_verificacion(cliente, activa: bool) -> None:
    settings = ajustes(verificacion_activa=activa)
    cliente.app.dependency_overrides[get_settings] = lambda: settings


def textos_guardados(fabrica) -> str:
    """Todo lo guardado en evaluaciones, verificaciones y auditoría, como texto."""
    with fabrica() as s:
        filas = []
        for modelo in (Evaluacion, VerificacionCodigo, Auditoria, Entrega):
            for fila in s.scalars(select(modelo)):
                filas.append([getattr(fila, c.key) for c in modelo.__table__.columns])
        return repr(filas)


def test_evaluacion_con_material_real_sin_verificacion(con_material_real, datos, evaluador):
    cliente, almacen, ejecutor = con_material_real
    preparar_entrega(datos, almacen)
    activar_verificacion(cliente, False)
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    assert leer(datos, evaluacion_id).estado == "borrador"
    solicitud = evaluador.solicitudes[0]
    assert "sobre funciones" in solicitud.texto_informe
    assert "def suma" in (solicitud.resumen_codigo or "")
    assert CORREO not in solicitud.texto_informe + (solicitud.resumen_codigo or "")
    assert "Ana Estudiante" not in solicitud.texto_informe
    assert solicitud.resultados_verificacion == {}
    assert ejecutor.llamadas == []
    with datos() as s:
        assert s.scalars(select(VerificacionCodigo)).first() is None


def test_evaluacion_con_verificacion_guarda_solo_tres_campos(con_material_real, datos, evaluador):
    cliente, almacen, ejecutor = con_material_real
    preparar_entrega(datos, almacen)
    activar_verificacion(cliente, True)
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    assert leer(datos, evaluacion_id).estado == "borrador"
    assert len(ejecutor.llamadas) == 1
    esperado = {"codigo_salida": 0, "tiene_error": False, "ejecucion_exitosa": True}
    assert evaluador.solicitudes[0].resultados_verificacion == esperado
    with datos() as s:
        fila = s.scalars(select(VerificacionCodigo)).one()
        assert fila.evaluacion_id == evaluacion_id
        assert fila.metricas == esperado
    guardado = textos_guardados(datos)
    assert MARCADOR_SALIDA not in guardado and MARCADOR_ERROR not in guardado
    solicitud = repr(evaluador.solicitudes[0])
    assert MARCADOR_SALIDA not in solicitud and MARCADOR_ERROR not in solicitud
    for ruta in (f"/api/evaluaciones/{evaluacion_id}", f"/api/evaluaciones/{evaluacion_id}/traza"):
        texto = cliente.get(ruta, headers=auth(ID_DOCENTE)).text
        assert MARCADOR_SALIDA not in texto and MARCADOR_ERROR not in texto
    traza = cliente.get(f"/api/evaluaciones/{evaluacion_id}/traza", headers=auth(ID_DOCENTE)).json()
    assert traza["verificacion"] == esperado


def test_traza_sin_verificacion_es_null(con_material_real, datos):
    cliente, almacen, _ = con_material_real
    preparar_entrega(datos, almacen)
    activar_verificacion(cliente, False)
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    traza = cliente.get(f"/api/evaluaciones/{evaluacion_id}/traza", headers=auth(ID_DOCENTE)).json()
    assert traza["verificacion"] is None


def test_entrega_sin_pdf_ni_codigo_legible_queda_error(con_material_real, datos, evaluador):
    cliente, almacen, _ = con_material_real
    with datos() as s:
        entrega = s.get(Entrega, 1)
        entrega.pdf_path = None
        entrega.codigo_zip_path = None
        entrega.github_url = "https://github.com/ana/lab"
        s.commit()
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    ev = leer(datos, evaluacion_id)
    assert ev.estado == "error"
    assert evaluador.solicitudes == []


def test_solo_zip_se_evalua(con_material_real, datos, evaluador):
    cliente, almacen, _ = con_material_real
    preparar_entrega(datos, almacen, pdf=False)
    activar_verificacion(cliente, False)
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    assert leer(datos, evaluacion_id).estado == "borrador"
    assert evaluador.solicitudes[0].texto_informe == ""


def test_archivo_ausente_en_el_almacen_queda_error_generico(con_material_real, datos):
    cliente, _almacen, _ = con_material_real
    with datos() as s:
        s.get(Entrega, 1).pdf_path = f"{ID_ESTUDIANTE}/1/informe.pdf"
        s.commit()
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    ev = leer(datos, evaluacion_id)
    assert ev.estado == "error"
    assert "almacén" not in (ev.error or "").lower()


# ---------- Detalle de evaluación ampliado ----------


def test_detalle_docente_incluye_laboratorio_y_estudiante(cliente, datos):
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    cuerpo = cliente.get(f"/api/evaluaciones/{evaluacion_id}", headers=auth(ID_DOCENTE)).json()
    assert cuerpo["laboratorio_id"] == 10
    assert cuerpo["estudiante_id"] == str(ID_ESTUDIANTE)
    assert cuerpo["estudiante_nombre"] == "Ana Estudiante"


def test_detalle_estudiante_sin_nombre(cliente, datos):
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    poner_estado(datos, evaluacion_id, "publicada")
    cuerpo = cliente.get(f"/api/evaluaciones/{evaluacion_id}", headers=auth(ID_ESTUDIANTE)).json()
    assert cuerpo["laboratorio_id"] == 10
    assert cuerpo["estudiante_id"] == str(ID_ESTUDIANTE)
    assert cuerpo["estudiante_nombre"] is None


def test_detalle_errores_con_forma_detail(cliente):
    respuesta = cliente.get("/api/evaluaciones/999", headers=auth(ID_DOCENTE))
    assert respuesta.status_code == 404
    assert isinstance(respuesta.json()["detail"], str)
    assert json.loads(respuesta.text).keys() == {"detail"}
