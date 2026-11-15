"""Pruebas de límites de tamaño, mensajes de validación en español y CORS (seguridad)."""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.errores import registrar_manejadores
from app.main import crear_app
from app.services.rubricas import (
    MAX_CRITERIOS,
    MAX_DESCRIPTOR,
    MAX_NIVELES,
    MAX_NOMBRE,
    validar_rubrica,
)
from tests.test_auth import ajustes, preparar
from tests.test_cohortes_laboratorios import DOC, assert_error, lab
from tests.test_validador_rubricas import rubrica_valida

CARPETA_DEMO = Path(__file__).resolve().parents[1] / "rubricas_demo"


# ---------- LaboratorioEntrada ----------


@pytest.mark.parametrize(
    ("campo", "maximo"),
    [("codigo", 50), ("titulo", 200), ("descripcion", 5000), ("objetivos", 5000)],
)
def test_laboratorio_texto_demasiado_largo_422(cliente_api, campo, maximo):
    cuerpo = {**lab("L1"), campo: "Z" * (maximo + 1)}
    r = cliente_api.post("/api/laboratorios", json=cuerpo, headers=DOC)
    assert_error(r, 422, f"{campo}: es demasiado largo (máximo {maximo} caracteres)")
    assert "ZZZZ" not in r.text


@pytest.mark.parametrize(
    ("campo", "maximo"),
    [("codigo", 50), ("titulo", 200), ("descripcion", 5000), ("objetivos", 5000)],
)
def test_laboratorio_texto_en_el_limite_se_acepta(cliente_api, campo, maximo):
    cuerpo = {**lab("L1"), campo: "Z" * maximo}
    r = cliente_api.post("/api/laboratorios", json=cuerpo, headers=DOC)
    assert r.status_code == 201, r.text


def test_criterio_id_demasiado_largo_422(cliente_api):
    cuerpo = {"criterios": [{"criterio_id": "C" * 101, "justificacion": "x"}], "motivo": "m"}
    r = cliente_api.patch("/api/evaluaciones/999/retroalimentacion", json=cuerpo, headers=DOC)
    assert_error(r, 422, "criterio_id: es demasiado largo (máximo 100 caracteres)")
    assert "CCCC" not in r.text


# ---------- Límites en el validador de rúbricas ----------


def _criterio(i: int, ponderacion: float, niveles: int = 2) -> dict:
    return {
        "id": f"c{i}",
        "competencia": "Programación",
        "nombre": f"Criterio {i}",
        "ponderacion": ponderacion,
        "niveles": [
            {"nombre": f"N{n}", "puntaje": round(5 - n * 0.4, 2), "descriptor": f"D{n}"}
            for n in range(niveles)
        ],
    }


def test_limites_exportados():
    assert (MAX_CRITERIOS, MAX_NIVELES) == (30, 10)


def test_rubrica_con_30_criterios_es_valida():
    rubrica = {"titulo": "T", "criterios": [_criterio(i, 100 / 30) for i in range(1, 31)]}
    assert validar_rubrica(rubrica) == []


def test_rubrica_con_31_criterios_es_inconsistente():
    rubrica = {"titulo": "T", "criterios": [_criterio(i, 100 / 31) for i in range(1, 32)]}
    assert validar_rubrica(rubrica) == ["La rúbrica tiene 31 criterios; el máximo es 30."]


def test_criterio_con_10_niveles_es_valido():
    rubrica = {"titulo": "T", "criterios": [_criterio(1, 100, niveles=10)]}
    assert validar_rubrica(rubrica) == []


def test_criterio_con_11_niveles_es_inconsistente():
    rubrica = {"titulo": "T", "criterios": [_criterio(1, 100, niveles=11)]}
    assert validar_rubrica(rubrica) == [
        'Criterio "c1" (Criterio 1): tiene 11 niveles; el máximo es 10.'
    ]


def test_textos_demasiado_largos_son_inconsistencias():
    rubrica = rubrica_valida()
    rubrica["titulo"] = "T" * 301
    rubrica["criterios"][0]["nombre"] = "N" * (MAX_NOMBRE + 1)
    rubrica["criterios"][0]["competencia"] = "C" * (MAX_NOMBRE + 1)
    rubrica["criterios"][1]["id"] = "i" * 101
    rubrica["criterios"][1]["niveles"][0]["nombre"] = "A" * 201
    rubrica["criterios"][1]["niveles"][1]["descriptor"] = "D" * (MAX_DESCRIPTOR + 1)
    errores = validar_rubrica(rubrica)
    texto = " ".join(errores)
    assert "El título tiene 301 caracteres; el máximo es 300." in errores
    assert "el nombre tiene 301 caracteres; el máximo es 300." in texto
    assert "la competencia tiene 301 caracteres; el máximo es 300." in texto
    assert "el id tiene 101 caracteres; el máximo es 100." in texto
    assert "tiene un nombre de 201 caracteres; el máximo es 200." in texto
    assert f"tiene un descriptor de {MAX_DESCRIPTOR + 1} caracteres" in texto
    assert len(texto) < 3000  # las etiquetas recortan los textos enormes


@pytest.mark.parametrize("archivo", sorted(CARPETA_DEMO.glob("*.json")), ids=lambda p: p.name)
def test_rubricas_demo_siguen_siendo_validas(archivo):
    assert validar_rubrica(json.loads(archivo.read_text(encoding="utf-8"))) == []


def test_rubrica_enorme_rechazada_por_api(cliente_api):
    rubrica = {"titulo": "T", "criterios": [_criterio(i, 1) for i in range(1, 101)]}
    r = cliente_api.post("/api/rubricas/validar", json=rubrica, headers=DOC)
    assert r.status_code == 200
    assert r.json() == {
        "valida": False,
        "inconsistencias": ["La rúbrica tiene 100 criterios; el máximo es 30."],
    }


# ---------- Mensajes de validación sin traducción ----------


class _ConBooleano(BaseModel):
    activo: bool


def test_error_de_validacion_no_mapeado_es_generico_y_en_espanol():
    aplicacion = FastAPI()
    registrar_manejadores(aplicacion)

    @aplicacion.post("/prueba")
    def _prueba(cuerpo: _ConBooleano) -> dict[str, bool]:
        return {"activo": cuerpo.activo}

    r = TestClient(aplicacion).post("/prueba", json={"activo": "valor-raro-recibido"})
    assert r.status_code == 422
    assert r.json() == {"detail": "Datos de entrada no válidos: activo: valor no válido."}
    assert "valor-raro-recibido" not in r.text
    assert "Input should" not in r.text


# ---------- CORS ----------


def _cliente_cors(fabrica_api):
    s = ajustes(frontend_url="https://mi-front.vercel.app")
    return preparar(crear_app(s), fabrica_api, s)


@pytest.mark.parametrize("metodo", ["PATCH", "DELETE", "PUT", "POST"])
def test_cors_preflight_metodos_permitidos(fabrica_api, metodo):
    c = _cliente_cors(fabrica_api)
    pre = c.options(
        "/api/laboratorios/1",
        headers={
            "Origin": "https://mi-front.vercel.app",
            "Access-Control-Request-Method": metodo,
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert pre.status_code == 200
    assert pre.headers["access-control-allow-origin"] == "https://mi-front.vercel.app"
    assert metodo in pre.headers["access-control-allow-methods"]
    assert pre.headers.get("access-control-allow-credentials") in (None, "false")


def test_cors_metodo_no_listado_rechazado(fabrica_api):
    c = _cliente_cors(fabrica_api)
    pre = c.options(
        "/api/salud",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "TRACE"},
    )
    assert pre.status_code == 400


def test_cors_sin_credenciales(fabrica_api):
    c = _cliente_cors(fabrica_api)
    r = c.get("/api/salud", headers={"Origin": "http://localhost:3000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert r.headers.get("access-control-allow-credentials") in (None, "false")


def test_cors_origen_no_permitido_sin_cabeceras(fabrica_api):
    c = _cliente_cors(fabrica_api)
    pre = c.options(
        "/api/laboratorios/1",
        headers={"Origin": "https://malicioso.example", "Access-Control-Request-Method": "DELETE"},
    )
    assert "access-control-allow-origin" not in pre.headers
    assert "access-control-allow-credentials" not in pre.headers
