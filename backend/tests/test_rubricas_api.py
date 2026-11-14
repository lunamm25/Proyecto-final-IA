"""Pruebas de validación, versionado y lectura de rúbricas por API (RF-03 CA2, CA4, CA5)."""

import copy

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import RubricaVersion
from app.services import rubricas as servicio
from tests.test_auth import ID_DOCENTE, ID_ESTUDIANTE
from tests.test_cohortes_laboratorios import DOC, EST, assert_error, crear
from tests.test_validador_rubricas import rubrica_valida


def ruta_versiones(laboratorio_id: int) -> str:
    """Ruta para crear versiones de la rúbrica de un laboratorio."""
    return f"/api/laboratorios/{laboratorio_id}/rubrica/versiones"


def sin_niveles() -> dict:
    """Rúbrica con el criterio c2 sin niveles."""
    r = rubrica_valida()
    r["criterios"][1]["niveles"] = []
    return r


# ---------- POST /api/rubricas/validar ----------


def test_validar_estudiante_403(cliente_api):
    assert_error(cliente_api.post("/api/rubricas/validar", json=rubrica_valida(), headers=EST), 403)


def test_validar_sin_token_401(cliente_api):
    assert_error(cliente_api.post("/api/rubricas/validar", json=rubrica_valida()), 401)


def test_validar_rubrica_valida(cliente_api):
    r = cliente_api.post("/api/rubricas/validar", json=rubrica_valida(), headers=DOC)
    assert r.status_code == 200
    assert r.json() == {"valida": True, "inconsistencias": []}


def test_validar_rubrica_invalida(cliente_api):
    r = cliente_api.post("/api/rubricas/validar", json=sin_niveles(), headers=DOC)
    assert r.status_code == 200
    assert r.json() == {
        "valida": False,
        "inconsistencias": ['Criterio "c2" (Uso de Git): no tiene niveles de desempeño.'],
    }


@pytest.mark.parametrize("basura", [[1, 2], "texto", None, 5, {"criterios": "x"}])
def test_validar_basura_200_con_inconsistencias(cliente_api, basura):
    r = cliente_api.post("/api/rubricas/validar", json=basura, headers=DOC)
    assert r.status_code == 200
    assert r.json()["valida"] is False and r.json()["inconsistencias"]


def test_validar_sin_cuerpo_200(cliente_api):
    r = cliente_api.post("/api/rubricas/validar", headers=DOC)
    assert r.status_code == 200 and r.json()["valida"] is False


def test_validar_json_mal_formado_422_en_espanol(cliente_api):
    r = cliente_api.post(
        "/api/rubricas/validar",
        content=b"{no es json",
        headers=DOC | {"Content-Type": "application/json"},
    )
    assert_error(r, 422, "JSON está mal formado")


# ---------- POST /api/laboratorios/{id}/rubrica/versiones ----------


def test_versiones_estudiante_403(cliente_api):
    creado = crear(cliente_api)
    r = cliente_api.post(ruta_versiones(creado["id"]), json=rubrica_valida(), headers=EST)
    assert_error(r, 403)


def test_versiones_rubrica_invalida_422(cliente_api, fabrica_api):
    creado = crear(cliente_api)
    r = cliente_api.post(ruta_versiones(creado["id"]), json=sin_niveles(), headers=DOC)
    assert r.status_code == 422
    assert r.json() == {
        "detail": "La rúbrica tiene inconsistencias y no se puede guardar.",
        "inconsistencias": ['Criterio "c2" (Uso de Git): no tiene niveles de desempeño.'],
    }
    with fabrica_api() as s:
        assert s.query(RubricaVersion).count() == 0


@pytest.mark.parametrize("basura", [[1], "texto", None])
def test_versiones_basura_422(cliente_api, basura):
    creado = crear(cliente_api)
    r = cliente_api.post(ruta_versiones(creado["id"]), json=basura, headers=DOC)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str) and r.json()["inconsistencias"]


def test_versiones_laboratorio_inexistente_404(cliente_api):
    r = cliente_api.post(ruta_versiones(999), json=rubrica_valida(), headers=DOC)
    assert_error(r, 404, "El laboratorio no existe")


def test_versiones_laboratorio_inexistente_404_aunque_rubrica_invalida(cliente_api):
    assert_error(cliente_api.post(ruta_versiones(999), json=[], headers=DOC), 404)


def test_primera_y_segunda_version_inmutables(cliente_api):
    creado = crear(cliente_api)
    v1_contenido = rubrica_valida()
    r1 = cliente_api.post(ruta_versiones(creado["id"]), json=v1_contenido, headers=DOC)
    assert r1.status_code == 201
    v1 = r1.json()
    assert set(v1) == {"id", "version", "estado", "contenido", "creada_por", "creada_en"}
    assert v1["version"] == 1 and v1["estado"] == "aprobada"
    assert v1["contenido"] == v1_contenido
    assert v1["creada_por"] == str(ID_DOCENTE) and v1["creada_en"]

    v2_contenido = copy.deepcopy(v1_contenido)
    v2_contenido["titulo"] = "Laboratorio 1 (corregido)"
    r2 = cliente_api.post(ruta_versiones(creado["id"]), json=v2_contenido, headers=DOC)
    assert r2.status_code == 201
    assert r2.json()["version"] == 2 and r2.json()["id"] != v1["id"]


def test_version_anterior_queda_intacta(cliente_api, fabrica_api):
    creado = crear(cliente_api)
    original = rubrica_valida()
    v1 = cliente_api.post(ruta_versiones(creado["id"]), json=original, headers=DOC).json()
    cambiada = copy.deepcopy(original)
    cambiada["criterios"][0]["ponderacion"] = 50
    cambiada["criterios"][1]["ponderacion"] = 50
    cliente_api.post(ruta_versiones(creado["id"]), json=cambiada, headers=DOC)
    with fabrica_api() as s:
        fila = s.get(RubricaVersion, v1["id"])
        assert fila.version == 1 and fila.contenido == original and fila.estado == "aprobada"
        assert s.query(RubricaVersion).count() == 2


def test_versiones_numeradas_por_laboratorio(cliente_api):
    a, b = crear(cliente_api, "L1"), crear(cliente_api, "L2")
    cliente_api.post(ruta_versiones(a["id"]), json=rubrica_valida(), headers=DOC)
    r = cliente_api.post(ruta_versiones(b["id"]), json=rubrica_valida(), headers=DOC)
    assert r.json()["version"] == 1


def test_choque_de_unicidad_responde_409(cliente_api, monkeypatch):
    creado = crear(cliente_api)

    def _choca(*_args, **_kwargs):
        raise IntegrityError("insert", {}, Exception("duplicate key"))

    monkeypatch.setattr(servicio, "_rubrica_del_laboratorio", _choca)
    r = cliente_api.post(ruta_versiones(creado["id"]), json=rubrica_valida(), headers=DOC)
    assert_error(r, 409, "al mismo tiempo")


# ---------- GET /api/laboratorios/{id}/rubrica ----------


def test_vigente_sin_versiones_404(cliente_api):
    creado = crear(cliente_api)
    r = cliente_api.get(f"/api/laboratorios/{creado['id']}/rubrica", headers=EST)
    assert_error(r, 404, "El laboratorio aún no tiene rúbrica aprobada")


def test_vigente_laboratorio_inexistente_404(cliente_api):
    assert_error(cliente_api.get("/api/laboratorios/999/rubrica", headers=EST), 404)


def test_vigente_sin_token_401(cliente_api):
    assert_error(cliente_api.get("/api/laboratorios/1/rubrica"), 401)


def test_vigente_devuelve_la_mayor_y_estudiante_puede_leer(cliente_api):
    creado = crear(cliente_api)
    for titulo in ("v1", "v2", "v3"):
        cuerpo = rubrica_valida() | {"titulo": titulo}
        cliente_api.post(ruta_versiones(creado["id"]), json=cuerpo, headers=DOC)
    r = cliente_api.get(f"/api/laboratorios/{creado['id']}/rubrica", headers=EST)
    assert r.status_code == 200
    assert r.json()["version"] == 3 and r.json()["contenido"]["titulo"] == "v3"


def test_vigente_ignora_borradores(cliente_api, fabrica_api):
    creado = crear(cliente_api)
    v1 = cliente_api.post(ruta_versiones(creado["id"]), json=rubrica_valida(), headers=DOC).json()
    with fabrica_api() as s:
        rubrica_id = s.get(RubricaVersion, v1["id"]).rubrica_id
        s.add(RubricaVersion(rubrica_id=rubrica_id, version=2, estado="borrador",
                             contenido={"titulo": "borrador"}, creada_por=ID_ESTUDIANTE))
        s.commit()
        assert servicio.obtener_version_vigente(s, creado["id"]).version == 1
    r = cliente_api.get(f"/api/laboratorios/{creado['id']}/rubrica", headers=EST)
    assert r.json()["version"] == 1


def test_obtener_version_vigente_none_sin_rubrica(cliente_api, fabrica_api):
    creado = crear(cliente_api)
    with fabrica_api() as s:
        assert servicio.obtener_version_vigente(s, creado["id"]) is None


def test_openapi_lista_los_endpoints_con_bearer(cliente_api):
    paths = cliente_api.get("/openapi.json").json()["paths"]
    esperados = {
        ("/api/cohortes", "get"),
        ("/api/laboratorios", "post"),
        ("/api/laboratorios/{laboratorio_id}", "put"),
        ("/api/laboratorios/{laboratorio_id}", "delete"),
        ("/api/rubricas/validar", "post"),
        ("/api/laboratorios/{laboratorio_id}/rubrica/versiones", "post"),
        ("/api/laboratorios/{laboratorio_id}/rubrica", "get"),
    }
    for ruta, metodo in esperados:
        assert paths[ruta][metodo]["security"] == [{"HTTPBearer": []}], (ruta, metodo)
