"""Pruebas de POST /api/laboratorios/{id}/rubrica/extraer (RF-03 CA1): PDF → rúbrica propuesta."""

import copy
import json
import sys

import pytest
from sqlalchemy import func, select

from app.api.deps import obtener_extractor_rubrica
from app.config import get_settings
from app.models import Auditoria, Laboratorio, RubricaVersion
from app.services import extractor_rubrica, rubricas_ia
from app.services.archivos import ArchivoEntrada
from app.services.errores import ArchivoDemasiadoGrandeError
from app.services.evaluaciones import ConfigEvaluacion
from app.services.extractor_rubrica import RubricaExtraida
from tests.dobles_entregas import pdf_con_texto, pdf_sin_texto
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE, ajustes, con_token, token_hs
from tests.test_secretos import CLAVE_EXACTA, TEXTO_SENSIBLE, sin_fragmentos
from tests.test_validador_rubricas import rubrica_valida

URL = "/api/laboratorios/10/rubrica/extraer"
TEXTO_PDF = "Enunciado del laboratorio 1. Rubrica: criterio C1 calidad del codigo 60 por ciento."
PDF_OK = pdf_con_texto(TEXTO_PDF)
CRUDO = '{"crudo": "RESPUESTA_CRUDA_EXTRACCION"}'
MSG_GENERICO = (
    "No se pudo extraer la rúbrica automáticamente. Inténtalo de nuevo o créala a mano."
)


def auth(usuario) -> dict[str, str]:
    return con_token(token_hs(usuario))


class ExtractorFalso:
    """Extractor inyectable: devuelve una rúbrica fija o lanza una excepción (sin IA real)."""

    def __init__(self) -> None:
        self.rubrica = rubrica_valida()
        self.excepcion: Exception | None = None
        self.llamadas: list[tuple[str, object]] = []

    def __call__(self, texto, config) -> RubricaExtraida:
        self.llamadas.append((texto, config))
        if self.excepcion is not None:
            raise self.excepcion
        return RubricaExtraida(
            rubrica=copy.deepcopy(self.rubrica), version_prompt="1.0", respuestas_crudas=[CRUDO]
        )


@pytest.fixture
def extractor() -> ExtractorFalso:
    return ExtractorFalso()


@pytest.fixture
def cliente(cliente_api, fabrica_api, extractor):
    """App con un laboratorio (id 10), Settings con clave inventada y extractor falso."""
    with fabrica_api() as s:
        s.add(Laboratorio(id=10, cohorte_id=1, codigo="LAB01", titulo="Funciones"))
        s.commit()
    cliente_api.app.dependency_overrides[get_settings] = lambda: ajustes(
        gemini_api_key=CLAVE_EXACTA
    )
    cliente_api.app.dependency_overrides[obtener_extractor_rubrica] = lambda: extractor
    return cliente_api


def subir(cliente, datos: bytes = PDF_OK, usuario=ID_DOCENTE, url=URL, tipo="application/pdf"):
    archivos = {"archivo": ("enunciado.pdf", datos, tipo)}
    return cliente.post(url, files=archivos, headers=auth(usuario))


def auditorias(fabrica, accion: str) -> list[Auditoria]:
    with fabrica() as s:
        return list(s.scalars(select(Auditoria).where(Auditoria.accion == accion)))


def versiones(fabrica) -> int:
    with fabrica() as s:
        return s.scalar(select(func.count(RubricaVersion.id)))


def assert_detalle(respuesta, codigo: int, fragmento: str) -> None:
    assert respuesta.status_code == codigo, respuesta.text
    assert set(respuesta.json()) == {"detail"}
    assert fragmento in respuesta.json()["detail"]


# ---------- Permisos ----------


def test_sin_token_401(cliente):
    r = cliente.post(URL, files={"archivo": ("e.pdf", PDF_OK, "application/pdf")})
    assert_detalle(r, 401, "token")


def test_estudiante_403(cliente, extractor):
    assert_detalle(subir(cliente, usuario=ID_ESTUDIANTE), 403, "permisos")
    assert extractor.llamadas == []


@pytest.mark.parametrize("usuario", [ID_DOCENTE, ID_ADMIN])
def test_docente_y_admin_200(cliente, extractor, usuario):
    r = subir(cliente, usuario=usuario)
    assert r.status_code == 200, r.text
    assert r.json() == {"rubrica": rubrica_valida(), "valida": True, "inconsistencias": []}
    texto, config = extractor.llamadas[0]
    assert TEXTO_PDF in texto
    assert config.proveedor == "gemini"


# ---------- Validación del archivo ----------


def test_pdf_falso_422(cliente, extractor):
    assert_detalle(subir(cliente, b"esto no es un PDF"), 422, "no es un PDF válido")
    assert extractor.llamadas == []


def test_tipo_no_pdf_422(cliente, extractor):
    assert_detalle(subir(cliente, tipo="image/png"), 422, "no es un PDF válido")
    assert extractor.llamadas == []


def test_pdf_mayor_de_20_mb_413(cliente, extractor):
    datos = b"%PDF-1.4\n" + b"0" * (20 * 1024 * 1024)
    assert_detalle(subir(cliente, datos), 413, "20 MB")
    assert extractor.llamadas == []


class FlujoContador:
    """Flujo de tamaño virtual que cuenta los bytes leídos."""

    def __init__(self, tamano: int) -> None:
        self.restante = tamano
        self.leidos = 0

    def read(self, n: int = -1) -> bytes:
        n = self.restante if n < 0 else min(n, self.restante)
        self.restante -= n
        self.leidos += n
        return b"%" * n


def test_pdf_grande_se_rechaza_sin_leer_todo():
    flujo = FlujoContador(200 * 1024 * 1024)
    with pytest.raises(ArchivoDemasiadoGrandeError):
        rubricas_ia.leer_pdf_enunciado(ArchivoEntrada(flujo=flujo, content_type="application/pdf"))
    assert flujo.leidos <= 21 * 1024 * 1024


def test_pdf_sin_texto_422(cliente, extractor):
    assert_detalle(subir(cliente, pdf_sin_texto()), 422, "El PDF no tiene texto extraíble")
    assert extractor.llamadas == []


def test_sin_archivo_422(cliente):
    r = cliente.post(URL, headers=auth(ID_DOCENTE))
    assert_detalle(r, 422, "archivo: es obligatorio")


def test_laboratorio_inexistente_404(cliente, extractor):
    r = subir(cliente, url="/api/laboratorios/999/rubrica/extraer")
    assert_detalle(r, 404, "El laboratorio no existe")
    assert extractor.llamadas == []


# ---------- Resultado ----------


def test_rubrica_inconsistente_valida_false(cliente, extractor):
    extractor.rubrica["criterios"][0]["ponderacion"] = 50
    r = subir(cliente)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["valida"] is False
    assert cuerpo["inconsistencias"] == ["Las ponderaciones suman 90 % y deben sumar 100 %."]
    assert cuerpo["rubrica"]["criterios"][0]["ponderacion"] == 50


def test_no_guarda_version_y_audita(cliente, fabrica_api):
    r = subir(cliente)
    assert r.status_code == 200
    assert versiones(fabrica_api) == 0
    assert "RESPUESTA_CRUDA_EXTRACCION" not in r.text
    filas = auditorias(fabrica_api, "extraer_rubrica_ia")
    assert len(filas) == 1
    fila = filas[0]
    assert (fila.entidad, fila.entidad_id, fila.usuario_id) == ("laboratorios", "10", ID_DOCENTE)
    d = fila.despues
    assert d["laboratorio_id"] == 10
    assert d["version_prompt"] == "1.0"
    assert (d["proveedor"], d["modelo"]) == ("gemini", get_settings().llm_model)
    assert (d["criterios"], d["valida"], d["inconsistencias"]) == (2, True, 0)
    assert d["respuestas_crudas"] == [CRUDO]
    assert d["tamano_pdf_bytes"] == len(PDF_OK)
    assert TEXTO_PDF not in json.dumps(d, ensure_ascii=False)


# ---------- Fallos de la IA ----------


def test_fallo_de_la_ia_mensaje_generico_y_detalle_tachado(cliente, extractor, fabrica_api):
    try:
        raise RuntimeError(TEXTO_SENSIBLE)
    except RuntimeError as causa:
        error = extractor_rubrica.ExtraccionRubricaError(TEXTO_SENSIBLE, [TEXTO_SENSIBLE])
        error.__cause__ = causa
    extractor.excepcion = error
    r = subir(cliente)
    assert r.status_code == 503
    assert r.json() == {"detail": MSG_GENERICO}
    sin_fragmentos(r.text)
    assert versiones(fabrica_api) == 0
    filas = auditorias(fabrica_api, "extraer_rubrica_ia_error")
    assert len(filas) == 1
    guardado = json.dumps(filas[0].despues, ensure_ascii=False)
    sin_fragmentos(guardado)
    assert "***" in filas[0].despues["error"]["mensaje"]
    assert "***" in filas[0].despues["error"]["causa"]
    assert TEXTO_PDF not in guardado
    assert auditorias(fabrica_api, "extraer_rubrica_ia") == []


def test_excepcion_cualquiera_es_generica(cliente, extractor, fabrica_api):
    extractor.excepcion = ValueError("formato raro " + CLAVE_EXACTA)
    r = subir(cliente)
    assert r.json() == {"detail": MSG_GENERICO}
    assert r.status_code == 503
    sin_fragmentos(json.dumps(auditorias(fabrica_api, "extraer_rubrica_ia_error")[0].despues))


def test_modulo_de_ia_ausente_es_generico(cliente, fabrica_api, monkeypatch):
    del cliente.app.dependency_overrides[obtener_extractor_rubrica]
    monkeypatch.setitem(sys.modules, "app.ia.rubricas", None)
    r = subir(cliente)
    assert r.status_code == 503
    assert r.json() == {"detail": MSG_GENERICO}
    fila = auditorias(fabrica_api, "extraer_rubrica_ia_error")[0]
    assert fila.despues["error"]["tipo"] == "ExtractorNoDisponibleError"


def test_adaptador_modulo_ausente_lanza_error_de_dominio(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.ia.rubricas", None)
    config = ConfigEvaluacion("gemini", "modelo-de-prueba", 0.1)
    with pytest.raises(extractor_rubrica.ExtractorNoDisponibleError) as error:
        extractor_rubrica.extraer_rubrica_con_ia("texto", config)
    assert error.value.mensaje == extractor_rubrica.MSG_NO_DISPONIBLE


# ---------- Integración sin red con el FakeProvider de Rol 1 ----------


def test_integracion_con_fake_provider(cliente, fabrica_api, monkeypatch):
    from app.ia import rubricas as ia_rubricas
    from app.ia.providers import FakeProvider

    del cliente.app.dependency_overrides[obtener_extractor_rubrica]
    proveedor = FakeProvider([rubrica_valida()])
    monkeypatch.setattr(extractor_rubrica, "construir_proveedor", lambda *_a, **_k: proveedor)
    r = subir(cliente)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["valida"] is True
    assert cuerpo["inconsistencias"] == []
    assert [c["id"] for c in cuerpo["rubrica"]["criterios"]] == ["c1", "c2"]
    assert TEXTO_PDF in proveedor.prompts_recibidos[0]
    d = auditorias(fabrica_api, "extraer_rubrica_ia")[0].despues
    assert d["version_prompt"] == ia_rubricas.VERSION_PROMPT_EXTRAER_RUBRICA
    assert json.loads(d["respuestas_crudas"][0])["titulo"] == "Laboratorio 1"


def test_integracion_fake_provider_json_invalido(cliente, fabrica_api, monkeypatch):
    from app.ia.providers import FakeProvider

    del cliente.app.dependency_overrides[obtener_extractor_rubrica]
    proveedor = FakeProvider(["no es json"] * 3)
    monkeypatch.setattr(extractor_rubrica, "construir_proveedor", lambda *_a, **_k: proveedor)
    r = subir(cliente)
    assert r.status_code == 503
    assert r.json() == {"detail": MSG_GENERICO}
    d = auditorias(fabrica_api, "extraer_rubrica_ia_error")[0].despues
    assert d["error"]["tipo"] == "ExtraccionRubricaError"
    assert d["error"]["respuestas_crudas"] == ["no es json"]

