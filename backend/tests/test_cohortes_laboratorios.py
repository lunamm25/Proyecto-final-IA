"""Pruebas de GET /api/cohortes y del CRUD de laboratorios (RF-02 CA1)."""

import pytest
from sqlalchemy import func, select

from app.models import Entrega, Laboratorio, Rubrica, RubricaVersion
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE, con_token, token_hs
from tests.test_validador_rubricas import rubrica_valida

EST = con_token(token_hs(ID_ESTUDIANTE))
DOC = con_token(token_hs(ID_DOCENTE))
ADM = con_token(token_hs(ID_ADMIN))


def lab(codigo: str = "L1", cohorte_id: int = 1, **extra) -> dict:
    """Cuerpo de laboratorio de ejemplo."""
    return {"cohorte_id": cohorte_id, "codigo": codigo, "titulo": f"Título {codigo}", **extra}


def crear(cliente, codigo: str = "L1", cohorte_id: int = 1, **extra) -> dict:
    """Crea un laboratorio como docente y devuelve el JSON."""
    r = cliente.post("/api/laboratorios", json=lab(codigo, cohorte_id, **extra), headers=DOC)
    assert r.status_code == 201, r.text
    return r.json()


def assert_error(respuesta, codigo: int, fragmento: str = "") -> None:
    """El error tiene el código esperado y la forma {"detail": "<texto>"}."""
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"detail"}
    assert isinstance(cuerpo["detail"], str) and cuerpo["detail"]
    assert fragmento in cuerpo["detail"]


# ---------- GET /api/cohortes ----------


def test_cohortes_sin_token_401(cliente_api):
    assert_error(cliente_api.get("/api/cohortes"), 401)


def test_cohortes_estudiante_estructura_y_orden(cliente_api):
    crear(cliente_api, "L2", descripcion="d", objetivos="o")
    crear(cliente_api, "L1")
    crear(cliente_api, "M1", cohorte_id=2)
    r = cliente_api.get("/api/cohortes", headers=EST)
    assert r.status_code == 200
    datos = r.json()
    assert [c["numero"] for c in datos] == [1, 2]
    assert set(datos[0]) == {"id", "nombre", "numero", "laboratorios"}
    assert [lab["codigo"] for lab in datos[0]["laboratorios"]] == ["L1", "L2"]
    l2 = datos[0]["laboratorios"][1]
    assert set(l2) == {
        "id", "cohorte_id", "codigo", "titulo", "descripcion", "objetivos",
        "version_rubrica_vigente",
    }
    assert l2["descripcion"] == "d" and l2["objetivos"] == "o" and l2["cohorte_id"] == 1
    assert l2["version_rubrica_vigente"] is None
    assert [lab["codigo"] for lab in datos[1]["laboratorios"]] == ["M1"]


def test_cohortes_indican_version_vigente(cliente_api):
    creado = crear(cliente_api, "L1")
    ruta = f"/api/laboratorios/{creado['id']}/rubrica/versiones"
    for _ in range(2):
        assert cliente_api.post(ruta, json=rubrica_valida(), headers=DOC).status_code == 201
    datos = cliente_api.get("/api/cohortes", headers=EST).json()
    assert datos[0]["laboratorios"][0]["version_rubrica_vigente"] == 2


# ---------- Permisos ----------


def test_estudiante_no_puede_crear_editar_ni_borrar(cliente_api):
    creado = crear(cliente_api)
    ruta = f"/api/laboratorios/{creado['id']}"
    assert_error(cliente_api.post("/api/laboratorios", json=lab("X"), headers=EST), 403)
    assert_error(cliente_api.put(ruta, json=lab("X"), headers=EST), 403)
    assert_error(cliente_api.delete(ruta, headers=EST), 403)


def test_sin_token_no_puede_crear(cliente_api):
    assert_error(cliente_api.post("/api/laboratorios", json=lab()), 401)


@pytest.mark.parametrize("cabecera", [DOC, ADM])
def test_docente_y_admin_crean_editan_y_borran(cliente_api, cabecera):
    cuerpo = lab("  L9  ", titulo=" Título L9 ")
    r = cliente_api.post("/api/laboratorios", json=cuerpo, headers=cabecera)
    assert r.status_code == 201
    creado = r.json()
    assert creado["codigo"] == "L9" and creado["titulo"] == "Título L9"
    assert creado["descripcion"] is None and creado["objetivos"] is None
    ruta = f"/api/laboratorios/{creado['id']}"
    r = cliente_api.put(ruta, json=lab("L9b", cohorte_id=2, objetivos="Aprender"), headers=cabecera)
    assert r.status_code == 200
    assert r.json() == {
        "id": creado["id"], "cohorte_id": 2, "codigo": "L9b", "titulo": "Título L9b",
        "descripcion": None, "objetivos": "Aprender",
    }
    r = cliente_api.delete(ruta, headers=cabecera)
    assert r.status_code == 204 and r.content == b""


# ---------- Validaciones ----------


def test_codigo_duplicado_al_crear_409(cliente_api):
    crear(cliente_api, "L1")
    r = cliente_api.post("/api/laboratorios", json=lab("L1", cohorte_id=2), headers=DOC)
    assert_error(r, 409, "Ya existe un laboratorio con el código L1")


def test_codigo_duplicado_al_editar_409(cliente_api):
    crear(cliente_api, "L1")
    otro = crear(cliente_api, "L2")
    r = cliente_api.put(f"/api/laboratorios/{otro['id']}", json=lab("L1"), headers=DOC)
    assert_error(r, 409, "código L1")


def test_editar_manteniendo_su_propio_codigo(cliente_api):
    creado = crear(cliente_api, "L1")
    r = cliente_api.put(
        f"/api/laboratorios/{creado['id']}", json=lab("L1", titulo="Nuevo"), headers=DOC
    )
    assert r.status_code == 200 and r.json()["titulo"] == "Nuevo"


def test_cohorte_inexistente_422(cliente_api):
    r = cliente_api.post("/api/laboratorios", json=lab(cohorte_id=99), headers=DOC)
    assert_error(r, 422, "La cohorte 99 no existe")


@pytest.mark.parametrize("campo", ["codigo", "titulo"])
def test_codigo_o_titulo_vacio_422(cliente_api, campo):
    cuerpo = lab() | {campo: "   "}
    assert_error(cliente_api.post("/api/laboratorios", json=cuerpo, headers=DOC), 422)


def test_falta_campo_obligatorio_422_en_espanol(cliente_api):
    r = cliente_api.post("/api/laboratorios", json={"cohorte_id": 1}, headers=DOC)
    assert_error(r, 422, "codigo: es obligatorio")


def test_editar_inexistente_404(cliente_api):
    assert_error(cliente_api.put("/api/laboratorios/999", json=lab(), headers=DOC), 404)


def test_borrar_inexistente_404(cliente_api):
    assert_error(cliente_api.delete("/api/laboratorios/999", headers=DOC), 404)


def test_id_no_numerico_422(cliente_api):
    assert_error(cliente_api.delete("/api/laboratorios/abc", headers=DOC), 422)


# ---------- DELETE con y sin entregas ----------


def _con_rubrica(cliente, codigo: str = "L1") -> dict:
    """Laboratorio con una versión de rúbrica aprobada."""
    creado = crear(cliente, codigo)
    r = cliente.post(
        f"/api/laboratorios/{creado['id']}/rubrica/versiones", json=rubrica_valida(), headers=DOC
    )
    assert r.status_code == 201
    return creado | {"version_id": r.json()["id"]}


def test_borrar_con_entregas_409(cliente_api, fabrica_api):
    creado = _con_rubrica(cliente_api)
    with fabrica_api() as s:
        s.add(
            Entrega(
                estudiante_id=ID_ESTUDIANTE,
                laboratorio_id=creado["id"],
                rubrica_version_id=creado["version_id"],
                pdf_path="entregas/a.pdf",
            )
        )
        s.commit()
    r = cliente_api.delete(f"/api/laboratorios/{creado['id']}", headers=DOC)
    assert_error(r, 409, "No se puede borrar: el laboratorio tiene entregas")
    with fabrica_api() as s:
        assert s.get(Laboratorio, creado["id"]) is not None
        assert s.get(RubricaVersion, creado["version_id"]) is not None


def test_borrar_sin_entregas_borra_rubrica_y_versiones(cliente_api, fabrica_api):
    creado = _con_rubrica(cliente_api)
    otro = _con_rubrica(cliente_api, "L2")
    assert cliente_api.delete(f"/api/laboratorios/{creado['id']}", headers=DOC).status_code == 204
    with fabrica_api() as s:
        assert s.get(Laboratorio, creado["id"]) is None
        assert s.scalar(select(func.count()).select_from(Rubrica)) == 1
        assert s.scalar(select(func.count()).select_from(RubricaVersion)) == 1
        assert s.get(RubricaVersion, otro["version_id"]) is not None
