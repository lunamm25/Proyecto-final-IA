"""Pruebas de POST y GET /api/entregas (RF-04): permisos, validación, Storage y auditoría.

Se usa un almacén en memoria (nunca la red ni el `.env`) y la SQLite de prueba.
"""

import io
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.api.deps import obtener_almacen
from app.config import get_settings
from app.db import get_db
from app.models import Auditoria, Entrega, Evaluacion, Laboratorio
from app.services import entregas as servicio
from app.services.almacen import AlmacenError, AlmacenSupabase
from app.services.entregas import ArchivoDemasiadoGrandeError, leer_limitado, validar_github_url
from app.services.errores import DatosInvalidosError
from tests.dobles_entregas import AlmacenMemoria, pdf_con_texto, pdf_sin_texto, zip_con
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE, ajustes, con_token, token_hs
from tests.test_evaluaciones import ID_OTRO

PDF_OK = pdf_con_texto("Informe del laboratorio de funciones en Python.")
ZIP_OK = zip_con({"main.py": "print('hola')\n"})
NOMBRE_MALICIOSO = "../../etc/passwd.pdf"


@pytest.fixture(autouse=True)
def sin_red_httpx(monkeypatch):
    """Falla si algún test intenta una conexión HTTP real."""

    def _prohibido(*_args, **_kwargs):
        raise AssertionError("No se permite usar la red en los tests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _prohibido)


@pytest.fixture
def almacen() -> AlmacenMemoria:
    return AlmacenMemoria()


@pytest.fixture
def api(cliente_api, datos, almacen):
    """Cliente con laboratorio 10 (rúbrica aprobada), laboratorio 11 (sin rúbrica) y almacén."""
    with datos() as s:
        s.add(Laboratorio(id=11, cohorte_id=1, codigo="LAB02", titulo="Sin rúbrica"))
        s.commit()
    cliente_api.app.dependency_overrides[obtener_almacen] = lambda: almacen
    return cliente_api


def auth(usuario: uuid.UUID) -> dict[str, str]:
    return con_token(token_hs(usuario))


def crear(
    cliente,
    usuario: uuid.UUID | None = ID_ESTUDIANTE,
    *,
    laboratorio_id: object = 10,
    pdf: bytes | None = PDF_OK,
    zip_: bytes | None = None,
    github_url: str | None = None,
    extras: str | None = None,
    nombre_pdf: str = "informe.pdf",
    tipo_pdf: str = "application/pdf",
    tipo_zip: str = "application/zip",
):
    archivos = {}
    if pdf is not None:
        archivos["pdf"] = (nombre_pdf, pdf, tipo_pdf)
    if zip_ is not None:
        archivos["zip"] = ("codigo.zip", zip_, tipo_zip)
    formulario: dict[str, object] = {}
    if laboratorio_id is not None:
        formulario["laboratorio_id"] = str(laboratorio_id)
    if github_url is not None:
        formulario["github_url"] = github_url
    if extras is not None:
        formulario["extras"] = extras
    cabeceras = auth(usuario) if usuario is not None else {}
    return cliente.post("/api/entregas", data=formulario, files=archivos or None, headers=cabeceras)


def entregas_en_bd(fabrica) -> list[Entrega]:
    with fabrica() as s:
        filas = list(s.scalars(select(Entrega).order_by(Entrega.id)))
        s.expunge_all()
        return filas


def auditorias_entregas(fabrica, accion: str = "crear_entrega") -> list[Auditoria]:
    with fabrica() as s:
        filas = list(
            s.scalars(
                select(Auditoria).where(Auditoria.entidad == "entregas", Auditoria.accion == accion)
            )
        )
        s.expunge_all()
        return filas


def assert_error(respuesta, codigo: int, fragmento: str | None = None) -> None:
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["detail"], str)
    if fragmento:
        assert fragmento.lower() in cuerpo["detail"].lower()


# ---------- Permisos ----------


def test_crear_sin_token_401(api):
    assert_error(crear(api, None), 401)


def test_estudiante_crea_a_su_nombre_201(api, datos, almacen):
    respuesta = crear(api, zip_=ZIP_OK, github_url="https://github.com/ana/lab-01")
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["estudiante"] == {"id": str(ID_ESTUDIANTE), "nombre": "Ana Estudiante"}
    assert cuerpo["laboratorio"] == {"id": 10, "codigo": "LAB01", "titulo": "Funciones"}
    assert cuerpo["rubrica_version_id"] == 1
    assert cuerpo["rubrica_version"] == 1
    assert cuerpo["tiene_pdf"] is True
    assert cuerpo["tiene_zip"] is True
    assert cuerpo["github_url"] == "https://github.com/ana/lab-01"
    assert cuerpo["ultima_evaluacion"] is None
    assert cuerpo["creada_en"]
    nueva = entregas_en_bd(datos)[-1]
    assert nueva.id == cuerpo["id"]
    assert nueva.estudiante_id == ID_ESTUDIANTE
    assert nueva.rubrica_version_id == 1


@pytest.mark.parametrize("usuario", [ID_DOCENTE, ID_ADMIN])
def test_docente_y_admin_no_crean_entregas_403(api, datos, usuario):
    antes = len(entregas_en_bd(datos))
    assert_error(crear(api, usuario), 403)
    assert len(entregas_en_bd(datos)) == antes


def test_respuesta_no_expone_rutas_del_bucket(api):
    cuerpo = crear(api, zip_=ZIP_OK).json()
    texto = json.dumps(cuerpo)
    assert "pdf_path" not in cuerpo and "codigo_zip_path" not in cuerpo
    assert "informe.pdf" not in texto and "codigo.zip" not in texto


# ---------- Validación de la petición ----------


def test_sin_pdf_zip_ni_github_422(api, datos):
    antes = len(entregas_en_bd(datos))
    assert_error(crear(api, pdf=None), 422, "al menos")
    assert len(entregas_en_bd(datos)) == antes


def test_github_vacio_cuenta_como_ausente_422(api):
    assert_error(crear(api, pdf=None, github_url="   "), 422, "al menos")


def test_solo_zip_201(api):
    respuesta = crear(api, pdf=None, zip_=ZIP_OK)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["tiene_pdf"] is False


def test_solo_github_201(api, almacen):
    respuesta = crear(api, pdf=None, github_url="https://github.com/ana/lab-01")
    assert respuesta.status_code == 201, respuesta.text
    assert almacen.subidas == []


def test_falta_laboratorio_422(api):
    assert_error(crear(api, laboratorio_id=None), 422)


def test_laboratorio_inexistente_422(api):
    assert_error(crear(api, laboratorio_id=999), 422, "laboratorio")


def test_laboratorio_sin_rubrica_vigente_422(api):
    assert_error(crear(api, laboratorio_id=11), 422, "rúbrica aprobada")


def test_laboratorio_no_numerico_422(api):
    assert_error(crear(api, laboratorio_id="abc"), 422)


def test_pdf_con_cabecera_falsa_422(api, almacen):
    respuesta = crear(api, pdf=b"<html>no soy un pdf</html>")
    assert_error(respuesta, 422, "PDF")
    assert almacen.subidas == []


def test_pdf_falso_aunque_el_content_type_diga_pdf_422(api):
    assert_error(crear(api, pdf=b"MZ\x90\x00ejecutable", tipo_pdf="application/pdf"), 422, "PDF")


def test_pdf_real_con_content_type_raro_422(api):
    assert_error(crear(api, tipo_pdf="text/html"), 422, "PDF")


def test_pdf_sin_texto_extraible_422(api, datos):
    antes = len(entregas_en_bd(datos))
    assert_error(crear(api, pdf=pdf_sin_texto()), 422, "texto extraíble")
    assert len(entregas_en_bd(datos)) == antes


def test_pdf_danado_422(api):
    assert_error(crear(api, pdf=b"%PDF-1.4\nbasura sin estructura"), 422, "PDF")


def test_pdf_demasiado_grande_413(api, monkeypatch):
    monkeypatch.setattr(servicio, "LIMITE_PDF_BYTES", 1024)
    assert_error(crear(api, pdf=PDF_OK + b" " * 2048), 413, "PDF")


def test_zip_mayor_de_20_mb_413(api, datos, almacen):
    grande = b"PK\x03\x04" + b"\x00" * (21 * 1024 * 1024)
    respuesta = crear(api, zip_=grande)
    assert_error(respuesta, 413, "20 MB")
    assert almacen.subidas == []
    assert len(entregas_en_bd(datos)) == 2


def test_zip_no_valido_422(api):
    assert_error(crear(api, zip_=b"PK\x03\x04esto no es un zip"), 422, "ZIP")


def test_zip_con_cabecera_mala_422(api):
    assert_error(crear(api, zip_=b"Rar!\x1a\x07\x00 no es zip"), 422, "ZIP")


def test_zip_con_demasiados_archivos_422(api, monkeypatch):
    monkeypatch.setattr(servicio, "MAX_ARCHIVOS_ZIP", 3)
    archivos = {f"a{i}.py": "x = 1\n" for i in range(5)}
    assert_error(crear(api, zip_=zip_con(archivos)), 422, "archivos")


def test_zip_declarado_mayor_de_100_mb_descomprimido_422(api, monkeypatch):
    monkeypatch.setattr(servicio, "MAX_DESCOMPRIMIDO_BYTES", 100)
    assert_error(crear(api, zip_=zip_con({"a.py": "x" * 500})), 422, "descomprimido")


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/ana/lab",
        "https://gitlab.com/ana/lab",
        "https://github.com.evil.com/ana/lab",
        "https://usuario:clave@github.com/ana/lab",
        "https://token@github.com/ana/lab",
        "https://github.com/ana/lab con espacios",
        "https://github.com/ana/lab?token=abc",
        "https://github.com/ana/lab#readme",
        "https://github.com:8443/ana/lab",
        "https://github.com/ana",
        "https://github.com/",
        "https://github.com/ana/..",
        "https://github.com/../lab",
        "javascript:alert(1)",
        "https://github.com/ana/" + "a" * 400,
        "https://github.com/ana/lab\n",
    ],
)
def test_github_url_invalida_422(api, url):
    assert_error(crear(api, github_url=url), 422, "GitHub")


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/ana/lab-01",
        "https://github.com/Ana-Perez/mi.repo_2",
        "https://github.com/ana/lab-01.git",
        "https://github.com/ana/lab-01/tree/main/src",
        "https://github.com/ana/lab-01/",
    ],
)
def test_github_url_valida(url):
    assert validar_github_url(url) == url


def test_github_url_se_recorta_de_espacios_externos():
    assert validar_github_url("  https://github.com/ana/lab  ") == "https://github.com/ana/lab"


def test_github_url_vacia_es_none():
    assert validar_github_url("") is None
    assert validar_github_url(None) is None


def test_extras_json_objeto_se_guarda(api, datos):
    extras = json.dumps({"video": "https://youtu.be/abc", "notas": "Entrega final"})
    respuesta = crear(api, extras=extras)
    assert respuesta.status_code == 201, respuesta.text
    assert entregas_en_bd(datos)[-1].extras == json.loads(extras)


@pytest.mark.parametrize(
    "extras",
    [
        "no es json",
        "[1, 2, 3]",
        json.dumps({"anidado": {"a": 1}}),
        json.dumps({"Clave Rara!": "x"}),
        json.dumps({"largo": "x" * 600}),
        json.dumps({f"k{i}": "v" for i in range(30)}),
        "x" * 5000,
    ],
)
def test_extras_invalidos_422(api, extras):
    assert_error(crear(api, extras=extras), 422, "extras")


# ---------- Lectura por bloques ----------


class FlujoContador:
    """Flujo binario de tamaño virtual que cuenta los bytes que se le leen."""

    def __init__(self, tamano: int) -> None:
        self.restante = tamano
        self.leidos = 0

    def read(self, n: int = -1) -> bytes:
        n = self.restante if n < 0 else min(n, self.restante)
        self.restante -= n
        self.leidos += n
        return b"\x00" * n


def test_leer_limitado_rechaza_sin_leer_todo():
    flujo = FlujoContador(200 * 1024 * 1024)
    with pytest.raises(ArchivoDemasiadoGrandeError):
        leer_limitado(flujo, 20 * 1024 * 1024, "El ZIP supera 20 MB.")
    assert flujo.leidos <= 20 * 1024 * 1024 + servicio.BLOQUE_LECTURA


def test_leer_limitado_acepta_justo_el_limite():
    assert len(leer_limitado(io.BytesIO(b"a" * 1000), 1000, "x")) == 1000


# ---------- Storage: rutas, fallos y auditoría ----------


def test_rutas_del_bucket_las_genera_el_backend(api, datos, almacen):
    respuesta = crear(api, zip_=ZIP_OK, nombre_pdf=NOMBRE_MALICIOSO)
    assert respuesta.status_code == 201, respuesta.text
    entrega_id = respuesta.json()["id"]
    esperado_pdf = f"{ID_ESTUDIANTE}/{entrega_id}/informe.pdf"
    esperado_zip = f"{ID_ESTUDIANTE}/{entrega_id}/codigo.zip"
    assert almacen.subidas == [esperado_pdf, esperado_zip]
    assert almacen.tipos[esperado_pdf] == "application/pdf"
    assert almacen.tipos[esperado_zip] == "application/zip"
    for ruta in almacen.subidas:
        assert "passwd" not in ruta and ".." not in ruta
    nueva = entregas_en_bd(datos)[-1]
    assert nueva.pdf_path == esperado_pdf
    assert nueva.codigo_zip_path == esperado_zip
    assert almacen.objetos[esperado_pdf] == PDF_OK


def test_fallo_de_subida_no_deja_entrega_ni_auditoria_y_borra_lo_subido(api, datos, almacen):
    almacen.fallar_en = 1  # el PDF se sube y el ZIP falla
    respuesta = crear(api, zip_=ZIP_OK)
    assert_error(respuesta, 503)
    assert "intenta" in respuesta.json()["detail"].lower()
    assert len(entregas_en_bd(datos)) == 2
    assert auditorias_entregas(datos) == []
    assert almacen.borrados == almacen.subidas
    assert almacen.objetos == {}


def test_fallo_de_subida_queda_en_auditoria_tachado(api, datos, almacen):
    clave = "clave-de-servicio-inventada-QUE-NO-DEBE-SALIR-987"
    settings = ajustes(supabase_service_key=clave)

    class AlmacenIndiscreto(AlmacenMemoria):
        def subir(self, ruta, datos, content_type):
            raise AlmacenError(f"fallo con {clave} en https://x.supabase.co/storage")

    api.app.dependency_overrides[obtener_almacen] = lambda: AlmacenIndiscreto()
    api.app.dependency_overrides[get_settings] = lambda: settings
    respuesta = crear(api)
    assert_error(respuesta, 503)
    assert clave not in respuesta.text
    fallos = auditorias_entregas(datos, "crear_entrega_fallida")
    assert len(fallos) == 1
    assert clave not in json.dumps(fallos[0].despues)
    assert "supabase.co" not in json.dumps(fallos[0].despues)


def test_fallo_en_el_commit_borra_lo_subido(api, datos, almacen):
    def _db():
        with datos() as s:

            def _commit_que_falla():
                raise OperationalError("COMMIT", {}, Exception("conexión perdida"))

            s.commit = _commit_que_falla
            yield s

    api.app.dependency_overrides[get_db] = _db
    respuesta = crear(api, zip_=ZIP_OK)
    assert_error(respuesta, 503)
    assert len(almacen.subidas) == 2
    assert sorted(almacen.borrados) == sorted(almacen.subidas)
    assert len(entregas_en_bd(datos)) == 2
    assert auditorias_entregas(datos) == []


def test_auditoria_de_creacion(api, datos):
    respuesta = crear(api, zip_=ZIP_OK, github_url="https://github.com/ana/lab")
    entrega_id = respuesta.json()["id"]
    filas = auditorias_entregas(datos)
    assert len(filas) == 1
    fila = filas[0]
    assert fila.usuario_id == ID_ESTUDIANTE
    assert fila.entidad_id == str(entrega_id)
    despues = fila.despues
    assert despues["laboratorio_id"] == 10
    assert despues["rubrica_version_id"] == 1
    assert despues["tiene_pdf"] is True and despues["tiene_zip"] is True
    assert despues["github_url"] == "https://github.com/ana/lab"
    assert despues["tamano_pdf"] == len(PDF_OK)
    assert despues["tamano_zip"] == len(ZIP_OK)
    assert "Informe del laboratorio" not in json.dumps(despues)


# ---------- Almacén real contra Supabase Storage (con transporte simulado) ----------

CLAVE_FALSA = "clave-de-servicio-inventada-para-tests-0123456789"


def almacen_simulado(manejador) -> AlmacenSupabase:
    settings = ajustes(supabase_service_key=CLAVE_FALSA, supabase_bucket="entregas")
    return AlmacenSupabase(settings, transporte=httpx.MockTransport(manejador))


def test_almacen_supabase_sube_con_cabeceras_y_ruta_correctas():
    vistas: list[httpx.Request] = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={"Key": "ok"})

    almacen_simulado(manejador).subir("u/1/informe.pdf", b"%PDF-1", "application/pdf")
    peticion = vistas[0]
    assert peticion.method == "POST"
    assert str(peticion.url).endswith("/storage/v1/object/entregas/u/1/informe.pdf")
    assert peticion.headers["authorization"] == f"Bearer {CLAVE_FALSA}"
    assert peticion.headers["apikey"] == CLAVE_FALSA
    assert peticion.headers["content-type"] == "application/pdf"
    assert peticion.headers["x-upsert"] == "false"


def test_almacen_supabase_descarga_y_borra():
    def manejador(peticion: httpx.Request) -> httpx.Response:
        if peticion.method == "GET":
            return httpx.Response(200, content=b"datos")
        assert peticion.method == "DELETE"
        assert json.loads(peticion.content) == {"prefixes": ["a/1/informe.pdf"]}
        return httpx.Response(200, json=[])

    almacen = almacen_simulado(manejador)
    assert almacen.descargar("a/1/informe.pdf") == b"datos"
    almacen.borrar(["a/1/informe.pdf"])


def test_almacen_supabase_error_no_revela_clave_ni_url():
    def manejador(_peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text=f"bad request {CLAVE_FALSA}")

    with pytest.raises(AlmacenError) as error:
        almacen_simulado(manejador).subir("a/1/informe.pdf", b"x", "application/pdf")
    assert CLAVE_FALSA not in str(error.value)
    assert "supabase.co" not in str(error.value)
    assert error.value.__cause__ is None


def test_almacen_supabase_fallo_de_conexion_es_almacen_error():
    def manejador(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"no conecta a {peticion.url}", request=peticion)

    with pytest.raises(AlmacenError) as error:
        almacen_simulado(manejador).descargar("a/1/informe.pdf")
    assert "supabase.co" not in str(error.value)
    assert CLAVE_FALSA not in str(error.value)


def test_almacen_supabase_sin_configurar_no_usa_la_red():
    almacen = AlmacenSupabase(ajustes(supabase_service_key=""))
    with pytest.raises(AlmacenError):
        almacen.subir("a/1/informe.pdf", b"x", "application/pdf")


def test_almacen_supabase_rechaza_rutas_raras():
    almacen = almacen_simulado(lambda _p: httpx.Response(200))
    for ruta in ["../x", "/abs/x", "a/../b", "a\\b", ""]:
        with pytest.raises(AlmacenError):
            almacen.subir(ruta, b"x", "application/pdf")


def test_bucket_por_defecto_es_entregas():
    assert ajustes().supabase_bucket == "entregas"
    assert ajustes().verificacion_activa is False


# ---------- GET /api/entregas ----------


def preparar_listado(fabrica) -> None:
    """Entregas 1 (Ana) y 2 (Otro) del fixture y 3, 4 de Ana con fechas y evaluaciones."""
    base = datetime(2026, 11, 10, tzinfo=UTC)
    with fabrica() as s:
        s.add(Laboratorio(id=12, cohorte_id=1, codigo="LAB03", titulo="Clases"))
        s.flush()
        s.get(Entrega, 1).creada_en = base
        s.get(Entrega, 2).creada_en = base + timedelta(days=1)
        s.add_all(
            [
                Entrega(
                    id=3,
                    estudiante_id=ID_ESTUDIANTE,
                    laboratorio_id=10,
                    rubrica_version_id=1,
                    pdf_path="p3",
                    codigo_zip_path="z3",
                    github_url="https://github.com/ana/lab",
                    creada_en=base + timedelta(days=2),
                ),
                Entrega(
                    id=4,
                    estudiante_id=ID_ESTUDIANTE,
                    laboratorio_id=12,
                    rubrica_version_id=1,
                    pdf_path=None,
                    codigo_zip_path="z4",
                    creada_en=base + timedelta(days=3),
                ),
            ]
        )
        s.flush()
        s.add_all(
            [
                Evaluacion(id=1, entrega_id=1, estado="error", creada_en=base),
                Evaluacion(
                    id=2,
                    entrega_id=1,
                    estado="publicada",
                    nota=Decimal("4.3"),
                    creada_en=base + timedelta(1),
                ),
                Evaluacion(
                    id=3, entrega_id=3, estado="borrador", nota=Decimal("3.5"), creada_en=base
                ),
                Evaluacion(
                    id=4, entrega_id=2, estado="en_revision", nota=Decimal("2.0"), creada_en=base
                ),
            ]
        )
        s.commit()


def listar(cliente, usuario: uuid.UUID, **parametros):
    return cliente.get("/api/entregas", params=parametros, headers=auth(usuario))


def test_listar_sin_token_401(api):
    assert_error(api.get("/api/entregas"), 401)


def test_estudiante_ve_solo_las_suyas_ordenadas(api, datos):
    preparar_listado(datos)
    respuesta = listar(api, ID_ESTUDIANTE)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert [i["id"] for i in cuerpo["items"]] == [4, 3, 1]
    assert cuerpo["total"] == 3
    assert cuerpo["limit"] == 20 and cuerpo["offset"] == 0
    assert {i["estudiante"]["id"] for i in cuerpo["items"]} == {str(ID_ESTUDIANTE)}


def test_estudiante_con_su_propio_id_200(api, datos):
    preparar_listado(datos)
    respuesta = listar(api, ID_ESTUDIANTE, estudiante_id=str(ID_ESTUDIANTE))
    assert respuesta.json()["total"] == 3


def test_estudiante_pide_las_de_otro_404(api, datos):
    preparar_listado(datos)
    assert_error(listar(api, ID_ESTUDIANTE, estudiante_id=str(ID_OTRO)), 404)


def test_docente_ve_todas(api, datos):
    preparar_listado(datos)
    cuerpo = listar(api, ID_DOCENTE).json()
    assert [i["id"] for i in cuerpo["items"]] == [4, 3, 2, 1]
    assert cuerpo["total"] == 4


def test_admin_filtra_por_estudiante(api, datos):
    preparar_listado(datos)
    cuerpo = listar(api, ID_ADMIN, estudiante_id=str(ID_OTRO)).json()
    assert [i["id"] for i in cuerpo["items"]] == [2]
    assert cuerpo["items"][0]["estudiante"] == {"id": str(ID_OTRO), "nombre": "Otro Estudiante"}


def test_filtro_por_laboratorio(api, datos):
    preparar_listado(datos)
    cuerpo = listar(api, ID_DOCENTE, laboratorio_id=12).json()
    assert [i["id"] for i in cuerpo["items"]] == [4]
    assert cuerpo["items"][0]["laboratorio"] == {"id": 12, "codigo": "LAB03", "titulo": "Clases"}


def test_paginacion(api, datos):
    preparar_listado(datos)
    cuerpo = listar(api, ID_DOCENTE, limit=2, offset=1).json()
    assert [i["id"] for i in cuerpo["items"]] == [3, 2]
    assert cuerpo["total"] == 4
    assert cuerpo["limit"] == 2 and cuerpo["offset"] == 1


@pytest.mark.parametrize("parametros", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_paginacion_fuera_de_rango_422(api, parametros):
    assert_error(listar(api, ID_DOCENTE, **parametros), 422)


def test_campos_del_item(api, datos):
    preparar_listado(datos)
    items = {i["id"]: i for i in listar(api, ID_DOCENTE).json()["items"]}
    tres = items[3]
    assert tres["tiene_pdf"] is True and tres["tiene_zip"] is True
    assert tres["github_url"] == "https://github.com/ana/lab"
    assert tres["rubrica_version"] == 1 and tres["rubrica_version_id"] == 1
    assert items[4]["tiene_pdf"] is False
    texto = json.dumps(items)
    assert "p3" not in texto and "z3" not in texto and "z4" not in texto
    assert "pdf_path" not in texto and "url_firmada" not in texto


def test_docente_ve_estado_y_nota_reales(api, datos):
    preparar_listado(datos)
    items = {i["id"]: i for i in listar(api, ID_DOCENTE).json()["items"]}
    assert items[1]["ultima_evaluacion"] == {"id": 2, "estado": "publicada", "nota": 4.3}
    assert items[3]["ultima_evaluacion"] == {"id": 3, "estado": "borrador", "nota": 3.5}
    assert items[2]["ultima_evaluacion"] == {"id": 4, "estado": "en_revision", "nota": 2.0}
    assert items[4]["ultima_evaluacion"] is None


def test_estudiante_no_ve_nota_no_publicada(api, datos):
    preparar_listado(datos)
    items = {i["id"]: i for i in listar(api, ID_ESTUDIANTE).json()["items"]}
    assert items[1]["ultima_evaluacion"] == {"id": 2, "estado": "publicada", "nota": 4.3}
    assert items[3]["ultima_evaluacion"] == {"id": 3, "estado": "pendiente_revision", "nota": None}
    assert items[4]["ultima_evaluacion"] is None


@pytest.mark.parametrize(
    ("estado", "visible"),
    [
        ("procesando", "procesando"),
        ("error", "error"),
        ("borrador", "pendiente_revision"),
        ("en_revision", "pendiente_revision"),
        ("aprobada", "pendiente_revision"),
        ("publicada", "publicada"),
    ],
)
def test_estado_visible_para_el_estudiante(api, datos, estado, visible):
    with datos() as s:
        s.add(Evaluacion(id=50, entrega_id=1, estado=estado, nota=Decimal("3.0")))
        s.commit()
    item = listar(api, ID_ESTUDIANTE).json()["items"][0]
    assert item["ultima_evaluacion"]["estado"] == visible
    assert item["ultima_evaluacion"]["nota"] == (3.0 if estado == "publicada" else None)


def test_servicio_estudiante_ajeno_lanza_no_encontrado(datos):
    from app.models import Perfil
    from app.services.errores import NoEncontradoError

    with datos() as s:
        perfil = s.get(Perfil, ID_ESTUDIANTE)
        with pytest.raises(NoEncontradoError):
            servicio.listar_entregas(
                s, perfil, estudiante_id=ID_OTRO, laboratorio_id=None, limit=20, offset=0
            )


def test_validar_github_url_lanza_datos_invalidos():
    with pytest.raises(DatosInvalidosError):
        validar_github_url("https://gitlab.com/a/b")
