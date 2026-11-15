"""Pruebas de gestión de usuarios y roles (RF-01 CA3): solo el admin puede usarla."""

import uuid

import pytest
from sqlalchemy import func, select

from app.models import Auditoria, Perfil
from app.services import usuarios as servicio
from app.services.errores import ConflictoError
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE, con_token, token_hs

EST = con_token(token_hs(ID_ESTUDIANTE))
DOC = con_token(token_hs(ID_DOCENTE))
ADM = con_token(token_hs(ID_ADMIN))
ID_ADMIN_2 = uuid.UUID("55555555-5555-5555-5555-555555555555")


def assert_error(respuesta, codigo: int, fragmento: str = "") -> None:
    """El error tiene el código esperado y la forma {"detail": "<texto>"}."""
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"detail"}
    assert isinstance(cuerpo["detail"], str) and cuerpo["detail"]
    assert fragmento in cuerpo["detail"]


@pytest.fixture
def cliente(fabrica_api, cliente_api):
    """Cliente con correos en estudiante y docente (el admin queda sin correo)."""
    with fabrica_api() as s:
        s.get(Perfil, ID_ESTUDIANTE).correo = "ana@ejemplo.com"
        s.get(Perfil, ID_DOCENTE).correo = "diego@ejemplo.com"
        s.commit()
    return cliente_api


def rol_en_bd(fabrica, usuario_id: uuid.UUID) -> str:
    """Rol guardado en la BD para un usuario."""
    with fabrica() as s:
        return s.get(Perfil, usuario_id).rol


def auditorias(fabrica) -> list[Auditoria]:
    """Todas las filas de auditoría."""
    with fabrica() as s:
        return list(s.scalars(select(Auditoria).order_by(Auditoria.id)))


def cambiar(cliente, usuario_id, cuerpo, headers=ADM):
    """PATCH /api/usuarios/{id}/rol."""
    return cliente.patch(f"/api/usuarios/{usuario_id}/rol", json=cuerpo, headers=headers)


# ---------- GET /api/usuarios ----------


def test_listar_sin_token_401(cliente):
    assert_error(cliente.get("/api/usuarios"), 401)


@pytest.mark.parametrize("headers", [EST, DOC], ids=["estudiante", "docente"])
def test_listar_sin_rol_admin_403(cliente, headers):
    assert_error(cliente.get("/api/usuarios", headers=headers), 403)


def test_listar_admin_200_campos_y_orden(cliente):
    r = cliente.get("/api/usuarios", headers=ADM)
    assert r.status_code == 200
    datos = r.json()
    assert [u["nombre"] for u in datos] == ["Alba Admin", "Ana Estudiante", "Diego Docente"]
    assert all(set(u) == {"id", "nombre", "correo", "rol"} for u in datos)
    assert datos[0] == {"id": str(ID_ADMIN), "nombre": "Alba Admin", "correo": None, "rol": "admin"}
    assert datos[1]["correo"] == "ana@ejemplo.com" and datos[1]["rol"] == "estudiante"
    assert datos[2]["id"] == str(ID_DOCENTE) and datos[2]["rol"] == "docente"


def test_listar_nombre_nulo_al_final(cliente, fabrica_api):
    with fabrica_api() as s:
        s.add(Perfil(id=uuid.uuid4(), nombre=None, rol="estudiante"))
        s.commit()
    datos = cliente.get("/api/usuarios", headers=ADM).json()
    assert len(datos) == 4 and datos[-1]["nombre"] is None


# ---------- PATCH /api/usuarios/{id}/rol: permisos ----------


def test_cambiar_sin_token_401(cliente):
    assert_error(cambiar(cliente, ID_ESTUDIANTE, {"rol": "docente"}, headers={}), 401)


@pytest.mark.parametrize("headers", [EST, DOC], ids=["estudiante", "docente"])
def test_cambiar_sin_rol_admin_403(cliente, fabrica_api, headers):
    assert_error(cambiar(cliente, ID_ESTUDIANTE, {"rol": "docente"}, headers), 403)
    assert rol_en_bd(fabrica_api, ID_ESTUDIANTE) == "estudiante"
    assert auditorias(fabrica_api) == []


# ---------- PATCH: cambio válido y auditoría ----------


def test_admin_cambia_estudiante_a_docente(cliente, fabrica_api):
    r = cambiar(cliente, ID_ESTUDIANTE, {"rol": "docente"})
    assert r.status_code == 200, r.text
    assert r.json() == {
        "id": str(ID_ESTUDIANTE), "nombre": "Ana Estudiante",
        "correo": "ana@ejemplo.com", "rol": "docente",
    }
    assert rol_en_bd(fabrica_api, ID_ESTUDIANTE) == "docente"


def test_auditoria_del_cambio_con_motivo(cliente, fabrica_api):
    cambiar(cliente, ID_ESTUDIANTE, {"rol": "docente", "motivo": "Monitora del curso"})
    [fila] = auditorias(fabrica_api)
    assert fila.usuario_id == ID_ADMIN
    assert fila.entidad == "perfiles" and fila.entidad_id == str(ID_ESTUDIANTE)
    assert fila.accion == "cambiar_rol"
    assert fila.antes == {"rol": "estudiante"} and fila.despues == {"rol": "docente"}
    assert fila.motivo == "Monitora del curso"
    assert fila.creado_en is not None


def test_auditoria_sin_motivo(cliente, fabrica_api):
    assert cambiar(cliente, ID_DOCENTE, {"rol": "estudiante"}).status_code == 200
    [fila] = auditorias(fabrica_api)
    assert fila.motivo is None
    assert fila.antes == {"rol": "docente"} and fila.despues == {"rol": "estudiante"}


def test_mismo_rol_200_sin_auditoria(cliente, fabrica_api):
    r = cambiar(cliente, ID_DOCENTE, {"rol": "docente", "motivo": "x"})
    assert r.status_code == 200 and r.json()["rol"] == "docente"
    assert auditorias(fabrica_api) == []


def test_admin_puede_nombrar_otro_admin(cliente, fabrica_api):
    assert cambiar(cliente, ID_DOCENTE, {"rol": "admin"}).status_code == 200
    assert rol_en_bd(fabrica_api, ID_DOCENTE) == "admin"


# ---------- PATCH: validaciones ----------


@pytest.mark.parametrize("rol", ["superusuario", "", "  ", "Admin"])
def test_rol_no_valido_422(cliente, fabrica_api, rol):
    assert_error(cambiar(cliente, ID_ESTUDIANTE, {"rol": rol}), 422, "Rol no válido")
    assert rol_en_bd(fabrica_api, ID_ESTUDIANTE) == "estudiante"
    assert auditorias(fabrica_api) == []


@pytest.mark.parametrize("cuerpo", [{"rol": None}, {"rol": 3}, {}, {"rol": ["admin"]}])
def test_rol_mal_tipado_422(cliente, fabrica_api, cuerpo):
    assert_error(cambiar(cliente, ID_ESTUDIANTE, cuerpo), 422, "rol")
    assert auditorias(fabrica_api) == []


def test_usuario_inexistente_404(cliente, fabrica_api):
    r = cambiar(cliente, uuid.uuid4(), {"rol": "docente"})
    assert_error(r, 404, "El usuario no existe.")
    assert auditorias(fabrica_api) == []


def test_id_no_uuid_422_en_espanol(cliente):
    r = cambiar(cliente, "no-es-un-uuid", {"rol": "docente"})
    assert_error(r, 422, "usuario_id")
    assert "UUID" in r.json()["detail"]
    assert "Input should" not in r.json()["detail"]


def test_admin_no_puede_quitarse_admin_409(cliente, fabrica_api):
    r = cambiar(cliente, ID_ADMIN, {"rol": "docente", "motivo": "prueba"})
    assert_error(r, 409, "propio rol")
    assert rol_en_bd(fabrica_api, ID_ADMIN) == "admin"
    assert auditorias(fabrica_api) == []


def test_admin_puede_degradar_a_otro_admin(cliente, fabrica_api):
    with fabrica_api() as s:
        s.add(Perfil(id=ID_ADMIN_2, nombre="Beto Admin", rol="admin"))
        s.commit()
    r = cambiar(cliente, ID_ADMIN_2, {"rol": "docente"})
    assert r.status_code == 200 and r.json()["rol"] == "docente"
    assert rol_en_bd(fabrica_api, ID_ADMIN_2) == "docente"
    assert len(auditorias(fabrica_api)) == 1


def test_ultimo_admin_no_puede_ser_degradado_409(fabrica_api):
    """Cubre la regla en el servicio aunque quien actúe no sea el propio admin."""
    with fabrica_api() as s:
        actor = s.get(Perfil, ID_DOCENTE)
        with pytest.raises(ConflictoError, match="al menos un administrador"):
            servicio.cambiar_rol(s, actor, ID_ADMIN, "estudiante", None)
    assert rol_en_bd(fabrica_api, ID_ADMIN) == "admin"
    assert auditorias(fabrica_api) == []


def test_contar_admins(fabrica_api):
    with fabrica_api() as s:
        assert servicio.contar_admins(s) == 1
        s.add(Perfil(id=ID_ADMIN_2, nombre="Beto", rol="admin"))
        s.commit()
        assert servicio.contar_admins(s) == 2
        assert s.scalar(select(func.count()).select_from(Auditoria)) == 0
