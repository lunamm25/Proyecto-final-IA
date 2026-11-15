"""Auditoría de laboratorios y versiones de rúbrica (M1): cada cambio deja su registro en la
misma transacción; si la auditoría no se puede escribir, el cambio tampoco se guarda."""

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import Auditoria, Laboratorio, RubricaVersion
from tests.test_auth import ID_DOCENTE
from tests.test_cohortes_laboratorios import DOC, crear, lab
from tests.test_validador_rubricas import rubrica_valida


def auditorias(fabrica, accion: str) -> list[Auditoria]:
    with fabrica() as s:
        filas = list(s.scalars(select(Auditoria).where(Auditoria.accion == accion)))
        s.expunge_all()
        return filas


def guardar_version(cliente, laboratorio_id: int):
    ruta = f"/api/laboratorios/{laboratorio_id}/rubrica/versiones"
    return cliente.post(ruta, json=rubrica_valida(), headers=DOC)


class FalloAuditoria:
    """Hace fallar el flush cuando la sesión intenta guardar una auditoría con `accion`."""

    def __init__(self, accion: str) -> None:
        self.accion = accion

    def __call__(self, session, _contexto, _instancias) -> None:
        if any(isinstance(o, Auditoria) and o.accion == self.accion for o in session.new):
            raise OperationalError("INSERT INTO auditoria", {}, Exception("disco lleno"))

    def __enter__(self) -> "FalloAuditoria":
        event.listen(Session, "before_flush", self)
        return self

    def __exit__(self, *_exc) -> None:
        event.remove(Session, "before_flush", self)


# ---------- Cada acción deja su auditoría ----------


def test_crear_laboratorio_audita(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1", descripcion="d", objetivos="o")
    (fila,) = auditorias(fabrica_api, "crear_laboratorio")
    assert fila.usuario_id == ID_DOCENTE
    assert (fila.entidad, fila.entidad_id) == ("laboratorios", str(creado["id"]))
    assert fila.antes is None
    assert fila.despues == {
        "cohorte_id": 1,
        "codigo": "L1",
        "titulo": "Título L1",
        "descripcion": "d",
        "objetivos": "o",
    }


def test_editar_laboratorio_audita_solo_lo_que_cambia(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1", descripcion="d")
    cuerpo = lab("L1", descripcion="d") | {"titulo": "Nuevo título"}
    r = cliente_api.put(f"/api/laboratorios/{creado['id']}", json=cuerpo, headers=DOC)
    assert r.status_code == 200, r.text
    (fila,) = auditorias(fabrica_api, "editar_laboratorio")
    assert fila.usuario_id == ID_DOCENTE
    assert fila.entidad_id == str(creado["id"])
    assert fila.antes == {"titulo": "Título L1"}
    assert fila.despues == {"titulo": "Nuevo título"}


def test_editar_sin_cambios_no_audita(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1")
    r = cliente_api.put(f"/api/laboratorios/{creado['id']}", json=lab("L1"), headers=DOC)
    assert r.status_code == 200
    assert auditorias(fabrica_api, "editar_laboratorio") == []


def test_borrar_laboratorio_audita_campos_y_versiones(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1", objetivos="o")
    for _ in range(2):
        assert guardar_version(cliente_api, creado["id"]).status_code == 201
    r = cliente_api.delete(f"/api/laboratorios/{creado['id']}", headers=DOC)
    assert r.status_code == 204
    (fila,) = auditorias(fabrica_api, "borrar_laboratorio")
    assert fila.usuario_id == ID_DOCENTE
    assert fila.entidad_id == str(creado["id"])
    assert fila.antes == {
        "cohorte_id": 1,
        "codigo": "L1",
        "titulo": "Título L1",
        "descripcion": None,
        "objetivos": "o",
        "versiones_rubrica_borradas": 2,
    }
    assert fila.despues is None


def test_guardar_version_rubrica_audita_sin_contenido(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1")
    r = guardar_version(cliente_api, creado["id"])
    assert r.status_code == 201
    version = r.json()
    with fabrica_api() as s:
        rubrica_id = s.get(RubricaVersion, version["id"]).rubrica_id
    (fila,) = auditorias(fabrica_api, "guardar_version_rubrica")
    assert fila.usuario_id == ID_DOCENTE
    assert (fila.entidad, fila.entidad_id) == ("rubrica_versiones", str(version["id"]))
    assert fila.despues == {
        "laboratorio_id": creado["id"],
        "rubrica_id": rubrica_id,
        "version": 1,
        "estado": "aprobada",
        "criterios": 2,
    }


# ---------- Si falla la auditoría, el cambio no se guarda ----------


def contar(fabrica, modelo) -> int:
    with fabrica() as s:
        return s.scalar(select(func.count()).select_from(modelo))


def test_fallo_auditoria_al_crear_no_guarda(cliente_api, fabrica_api):
    with FalloAuditoria("crear_laboratorio"), pytest.raises(OperationalError):
        cliente_api.post("/api/laboratorios", json=lab("L1"), headers=DOC)
    assert contar(fabrica_api, Laboratorio) == 0
    assert auditorias(fabrica_api, "crear_laboratorio") == []


def test_fallo_auditoria_al_editar_no_guarda(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1")
    cuerpo = lab("L1") | {"titulo": "Cambiado"}
    with FalloAuditoria("editar_laboratorio"), pytest.raises(OperationalError):
        cliente_api.put(f"/api/laboratorios/{creado['id']}", json=cuerpo, headers=DOC)
    with fabrica_api() as s:
        assert s.get(Laboratorio, creado["id"]).titulo == "Título L1"
    assert auditorias(fabrica_api, "editar_laboratorio") == []


def test_fallo_auditoria_al_borrar_no_borra(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1")
    assert guardar_version(cliente_api, creado["id"]).status_code == 201
    with FalloAuditoria("borrar_laboratorio"), pytest.raises(OperationalError):
        cliente_api.delete(f"/api/laboratorios/{creado['id']}", headers=DOC)
    assert contar(fabrica_api, Laboratorio) == 1
    assert contar(fabrica_api, RubricaVersion) == 1
    assert auditorias(fabrica_api, "borrar_laboratorio") == []


def test_fallo_auditoria_al_guardar_version_no_guarda(cliente_api, fabrica_api):
    creado = crear(cliente_api, "L1")
    with FalloAuditoria("guardar_version_rubrica"), pytest.raises(OperationalError):
        guardar_version(cliente_api, creado["id"])
    assert contar(fabrica_api, RubricaVersion) == 0
    assert auditorias(fabrica_api, "guardar_version_rubrica") == []
