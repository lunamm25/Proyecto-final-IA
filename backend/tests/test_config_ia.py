"""Pruebas de la configuración de IA (RF-10): GET/PUT /api/config-ia, solo admin."""

import sys

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.models import Auditoria, ConfigIA, Perfil
from app.services import config_ia as servicio
from app.services.evaluaciones import configuracion_ia
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE, ajustes, con_token, token_hs

EST = con_token(token_hs(ID_ESTUDIANTE))
DOC = con_token(token_hs(ID_DOCENTE))
ADM = con_token(token_hs(ID_ADMIN))
RUTA = "/api/config-ia"

CLAVE_GEMINI = "AIza-CLAVE-GEMINI-INVENTADA-123"
CLAVE_OPENAI = "sk-CLAVE-OPENAI-INVENTADA-456"
URL_PRIVADA = "https://usuario:contrasena@llm.ejemplo.com/v1"

CAMPOS_GET = {
    "proveedor",
    "modelo",
    "temperatura",
    "origen",
    "modelo_permitido",
    "actualizado_por",
    "actualizado_en",
    "temperatura_maxima",
    "claves",
    "proveedores_permitidos",
    "versiones_prompt",
}
VALIDO = {"proveedor": "gemini", "modelo": "gemini-2.5-flash", "temperatura": 0.05}


def assert_error(respuesta, codigo: int, fragmento: str = "") -> None:
    """El error tiene el código esperado y la forma {"detail": "<texto>"}."""
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"detail"}
    assert isinstance(cuerpo["detail"], str) and cuerpo["detail"]
    assert fragmento in cuerpo["detail"]


def usar_ajustes(cliente, **cambios: str) -> None:
    """Sustituye los Settings de la app por unos inventados para el test."""
    cliente.app.dependency_overrides[get_settings] = lambda: ajustes(**cambios)


def crear_fila(fabrica, proveedor="gemini", modelo="gemini-3.5-flash-lite", temperatura=0.1):
    """Inserta la fila única de config_ia actualizada por el admin."""
    with fabrica() as s:
        s.add(
            ConfigIA(
                id=1,
                proveedor=proveedor,
                modelo=modelo,
                temperatura=temperatura,
                actualizado_por=ID_ADMIN,
            )
        )
        s.commit()


def fila(fabrica) -> ConfigIA | None:
    """Fila de config_ia en la BD (o None)."""
    with fabrica() as s:
        return s.get(ConfigIA, 1)


def auditorias(fabrica) -> list[Auditoria]:
    """Todas las filas de auditoría."""
    with fabrica() as s:
        return list(s.scalars(select(Auditoria).order_by(Auditoria.id)))


def poner(cliente, cuerpo, headers=ADM):
    """PUT /api/config-ia."""
    return cliente.put(RUTA, json=cuerpo, headers=headers)


# ---------- Permisos ----------


def test_sin_token_401(cliente_api):
    assert_error(cliente_api.get(RUTA), 401)
    assert_error(cliente_api.put(RUTA, json=VALIDO), 401)


@pytest.mark.parametrize("headers", [EST, DOC], ids=["estudiante", "docente"])
def test_no_admin_403(cliente_api, fabrica_api, headers):
    assert_error(cliente_api.get(RUTA, headers=headers), 403)
    assert_error(poner(cliente_api, VALIDO, headers), 403)
    assert fila(fabrica_api) is None
    assert auditorias(fabrica_api) == []


def test_admin_get_200(cliente_api):
    r = cliente_api.get(RUTA, headers=ADM)
    assert r.status_code == 200, r.text
    assert set(r.json()) == CAMPOS_GET


# ---------- GET ----------


def test_get_con_fila(cliente_api, fabrica_api):
    crear_fila(fabrica_api, modelo="gemini-2.5-flash", temperatura=0.15)
    datos = cliente_api.get(RUTA, headers=ADM).json()
    assert (datos["proveedor"], datos["modelo"]) == ("gemini", "gemini-2.5-flash")
    assert datos["temperatura"] == pytest.approx(0.15)
    assert datos["origen"] == "base_de_datos"
    assert datos["modelo_permitido"] is True
    assert datos["actualizado_por"] == {"id": str(ID_ADMIN), "nombre": "Alba Admin"}
    assert datos["actualizado_en"]
    assert datos["temperatura_maxima"] == pytest.approx(0.2)


def test_get_sin_fila_usa_settings(cliente_api):
    usar_ajustes(cliente_api, llm_provider="gemini", llm_model="gemini-2.5-flash")
    datos = cliente_api.get(RUTA, headers=ADM).json()
    assert datos["origen"] == "entorno"
    assert (datos["proveedor"], datos["modelo"]) == ("gemini", "gemini-2.5-flash")
    assert datos["temperatura"] == pytest.approx(0.1)
    assert datos["actualizado_por"] is None and datos["actualizado_en"] is None


def test_get_sin_fila_acota_temperatura_del_entorno(cliente_api):
    usar_ajustes(cliente_api, llm_temperature="0.9")
    assert cliente_api.get(RUTA, headers=ADM).json()["temperatura"] == pytest.approx(0.2)


def test_get_claves_falsas_sin_configurar(cliente_api):
    claves = cliente_api.get(RUTA, headers=ADM).json()["claves"]
    assert claves == {
        "gemini_api_key_configurada": False,
        "openai_compat_api_key_configurada": False,
        "openai_compat_base_url_configurada": False,
    }


def test_get_claves_verdaderas_y_nunca_sus_valores(cliente_api):
    usar_ajustes(
        cliente_api,
        gemini_api_key=CLAVE_GEMINI,
        openai_compat_api_key=CLAVE_OPENAI,
        openai_compat_base_url=URL_PRIVADA,
    )
    r = cliente_api.get(RUTA, headers=ADM)
    assert r.json()["claves"] == {
        "gemini_api_key_configurada": True,
        "openai_compat_api_key_configurada": True,
        "openai_compat_base_url_configurada": True,
    }
    for secreto in (CLAVE_GEMINI, CLAVE_OPENAI, URL_PRIVADA, "llm.ejemplo.com", "contrasena"):
        assert secreto not in r.text


def test_get_clave_solo_espacios_no_cuenta(cliente_api):
    usar_ajustes(cliente_api, gemini_api_key="   ")
    claves = cliente_api.get(RUTA, headers=ADM).json()["claves"]
    assert claves["gemini_api_key_configurada"] is False


def test_versiones_prompt_reales(cliente_api):
    versiones = cliente_api.get(RUTA, headers=ADM).json()["versiones_prompt"]
    assert versiones["extraer_rubrica"] == "1.0"


def test_versiones_prompt_leen_solo_la_primera_linea(cliente_api, tmp_path, monkeypatch):
    (tmp_path / "evaluar.md").write_text("version: 2.3\n---\ncuerpo", encoding="utf-8")
    (tmp_path / "sin_version.md").write_text("Hola\nversion: 9.9\n", encoding="utf-8")
    (tmp_path / "vacio.md").write_text("", encoding="utf-8")
    (tmp_path / "notas.txt").write_text("version: 1.0", encoding="utf-8")
    monkeypatch.setattr(servicio, "CARPETA_PROMPTS", tmp_path)
    versiones = cliente_api.get(RUTA, headers=ADM).json()["versiones_prompt"]
    assert versiones == {"evaluar": "2.3", "sin_version": None, "vacio": None}


def test_get_no_importa_modulos_de_ia(cliente_api, monkeypatch):
    for nombre in [m for m in sys.modules if m == "app.ia" or m.startswith("app.ia.")]:
        monkeypatch.delitem(sys.modules, nombre)
    assert cliente_api.get(RUTA, headers=ADM).status_code == 200
    assert not [m for m in sys.modules if m == "app.ia" or m.startswith("app.ia.")]


def test_proveedores_permitidos_sin_fake(cliente_api):
    usar_ajustes(cliente_api, openai_compat_modelos="llama3.1:8b, qwen2.5:7b")
    proveedores = cliente_api.get(RUTA, headers=ADM).json()["proveedores_permitidos"]
    assert [p["proveedor"] for p in proveedores] == ["gemini", "openai_compat"]
    assert proveedores[0]["modelos"] == ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
    assert proveedores[1]["modelos"] == ["llama3.1:8b", "qwen2.5:7b"]
    assert all(p["etiqueta"] for p in proveedores)


def test_modelos_openai_descarta_nombres_invalidos_y_repetidos(cliente_api):
    usar_ajustes(cliente_api, openai_compat_modelos="llama3, ,mal nombre,llama3,x;rm,ok/m-1")
    proveedores = cliente_api.get(RUTA, headers=ADM).json()["proveedores_permitidos"]
    assert proveedores[1]["modelos"] == ["llama3", "ok/m-1"]


def test_openai_sin_lista_usa_llm_model_si_es_el_proveedor(cliente_api):
    usar_ajustes(cliente_api, llm_provider="openai_compat", llm_model="llama3.1:8b")
    proveedores = cliente_api.get(RUTA, headers=ADM).json()["proveedores_permitidos"]
    assert proveedores[1]["modelos"] == ["llama3.1:8b"]


def test_openai_sin_lista_ni_proveedor_queda_vacio(cliente_api):
    proveedores = cliente_api.get(RUTA, headers=ADM).json()["proveedores_permitidos"]
    assert proveedores[1]["modelos"] == []


def test_modelo_de_la_fila_fuera_de_lista(cliente_api, fabrica_api):
    crear_fila(fabrica_api, modelo="gemini-1.0-viejo")
    datos = cliente_api.get(RUTA, headers=ADM).json()
    assert datos["modelo"] == "gemini-1.0-viejo"
    assert datos["modelo_permitido"] is False


# ---------- PUT ----------


def test_put_valido_actualiza_y_audita(cliente_api, fabrica_api):
    crear_fila(fabrica_api)
    r = poner(cliente_api, VALIDO)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert set(datos) == CAMPOS_GET
    assert (datos["proveedor"], datos["modelo"]) == ("gemini", "gemini-2.5-flash")
    assert datos["temperatura"] == pytest.approx(0.05)
    assert datos["origen"] == "base_de_datos" and datos["modelo_permitido"] is True
    assert datos["actualizado_por"]["id"] == str(ID_ADMIN)
    guardada = fila(fabrica_api)
    assert (guardada.modelo, guardada.temperatura) == ("gemini-2.5-flash", pytest.approx(0.05))
    [registro] = auditorias(fabrica_api)
    assert registro.usuario_id == ID_ADMIN
    assert (registro.entidad, registro.entidad_id) == ("config_ia", "1")
    assert registro.accion == "cambiar_config_ia"
    assert registro.antes == {
        "proveedor": "gemini",
        "modelo": "gemini-3.5-flash-lite",
        "temperatura": 0.1,
    }
    assert registro.despues == {
        "proveedor": "gemini",
        "modelo": "gemini-2.5-flash",
        "temperatura": 0.05,
    }
    assert registro.motivo is None


def test_put_actualiza_quien_lo_cambio(cliente_api, fabrica_api):
    with fabrica_api() as s:
        s.add(ConfigIA(id=1, proveedor="gemini", modelo="gemini-2.5-flash", temperatura=0.1))
        s.commit()
    poner(cliente_api, VALIDO)
    assert fila(fabrica_api).actualizado_por == ID_ADMIN


def test_put_mismo_valor_200_sin_auditoria(cliente_api, fabrica_api):
    crear_fila(fabrica_api, modelo="gemini-2.5-flash", temperatura=0.05)
    antes = fila(fabrica_api).actualizado_en
    r = poner(
        cliente_api, {"proveedor": " gemini ", "modelo": " gemini-2.5-flash ", "temperatura": 0.05}
    )
    assert r.status_code == 200, r.text
    assert r.json()["modelo"] == "gemini-2.5-flash"
    assert auditorias(fabrica_api) == []
    assert fila(fabrica_api).actualizado_en == antes


def test_primer_put_crea_fila_y_audita_origen_entorno(cliente_api, fabrica_api):
    usar_ajustes(cliente_api, llm_provider="gemini", llm_model="gemini-2.5-flash")
    r = poner(
        cliente_api, {"proveedor": "gemini", "modelo": "gemini-2.5-flash", "temperatura": 0.1}
    )
    assert r.status_code == 200, r.text
    assert r.json()["origen"] == "base_de_datos"
    guardada = fila(fabrica_api)
    assert (guardada.proveedor, guardada.modelo) == ("gemini", "gemini-2.5-flash")
    assert guardada.actualizado_por == ID_ADMIN
    [registro] = auditorias(fabrica_api)
    assert registro.accion == "cambiar_config_ia"
    assert registro.antes == {
        "origen": "entorno",
        "proveedor": "gemini",
        "modelo": "gemini-2.5-flash",
        "temperatura": 0.1,
    }
    assert registro.despues == {
        "proveedor": "gemini",
        "modelo": "gemini-2.5-flash",
        "temperatura": 0.1,
    }


@pytest.mark.parametrize("proveedor", ["fake", "openai", "", "   ", "ollama"])
def test_put_proveedor_desconocido_422(cliente_api, fabrica_api, proveedor):
    r = poner(cliente_api, {**VALIDO, "proveedor": proveedor})
    assert_error(r, 422)
    assert "proveedor" in r.json()["detail"].lower()
    assert fila(fabrica_api) is None and auditorias(fabrica_api) == []


def test_put_proveedor_desconocido_mensaje(cliente_api):
    r = poner(cliente_api, {**VALIDO, "proveedor": "fake"})
    assert_error(r, 422, "Proveedor de IA no válido. Usa: gemini u openai_compat.")


def test_put_modelo_fuera_de_lista_422(cliente_api, fabrica_api):
    r = poner(cliente_api, {**VALIDO, "modelo": "gpt-4o"})
    assert_error(r, 422, "Modelo no permitido para gemini")
    assert "gemini-3.5-flash-lite" in r.json()["detail"]
    assert "gpt-4o" not in r.json()["detail"]
    assert fila(fabrica_api) is None and auditorias(fabrica_api) == []


@pytest.mark.parametrize(
    "modelo",
    ["gemini 2.5", "gemini-2.5-flash\nX", "a" * 101, "", "-empieza-mal", "x;rm -rf"],
    ids=["espacio", "salto", "largo", "vacio", "guion-inicial", "punto-y-coma"],
)
def test_put_modelo_con_formato_invalido_422(cliente_api, fabrica_api, modelo):
    assert_error(poner(cliente_api, {**VALIDO, "modelo": modelo}), 422, "modelo")
    assert fila(fabrica_api) is None and auditorias(fabrica_api) == []


def test_put_openai_con_lista(cliente_api, fabrica_api):
    usar_ajustes(cliente_api, openai_compat_modelos="llama3.1:8b,qwen2.5:7b")
    ok = poner(
        cliente_api, {"proveedor": "openai_compat", "modelo": "qwen2.5:7b", "temperatura": 0}
    )
    assert ok.status_code == 200, ok.text
    assert fila(fabrica_api).proveedor == "openai_compat"
    r = poner(cliente_api, {"proveedor": "openai_compat", "modelo": "mistral", "temperatura": 0})
    assert_error(r, 422, "Modelo no permitido para openai_compat")


def test_put_openai_sin_lista_acepta_solo_llm_model(cliente_api):
    usar_ajustes(cliente_api, llm_provider="openai_compat", llm_model="llama3.1:8b")
    otro = poner(cliente_api, {"proveedor": "openai_compat", "modelo": "mistral", "temperatura": 0})
    assert_error(otro, 422, "Modelo no permitido")
    ok = poner(
        cliente_api, {"proveedor": "openai_compat", "modelo": "llama3.1:8b", "temperatura": 0}
    )
    assert ok.status_code == 200, ok.text


def test_put_openai_sin_modelos_configurados_422(cliente_api, fabrica_api):
    r = poner(cliente_api, {"proveedor": "openai_compat", "modelo": "llama3", "temperatura": 0.1})
    assert_error(
        r,
        422,
        "No hay modelos configurados para openai_compat; "
        "define OPENAI_COMPAT_MODELOS en el servidor.",
    )
    assert fila(fabrica_api) is None


@pytest.mark.parametrize(
    ("temperatura", "fragmento"),
    [
        (0.21, "menor o igual que 0.2"),
        (-0.1, "mayor o igual que 0"),
        (0.9, "menor o igual que 0.2"),
        ("0.1", "debe ser un número"),
        (True, "debe ser un número"),
        (None, "debe ser un número"),
    ],
    ids=["0.21", "negativa", "0.9", "texto", "booleano", "nulo"],
)
def test_put_temperatura_invalida_422(cliente_api, fabrica_api, temperatura, fragmento):
    r = poner(cliente_api, {**VALIDO, "temperatura": temperatura})
    assert_error(r, 422, fragmento)
    assert "temperatura" in r.json()["detail"]
    assert fila(fabrica_api) is None


def test_put_temperatura_nan_422(cliente_api):
    cuerpo = b'{"proveedor": "gemini", "modelo": "gemini-2.5-flash", "temperatura": NaN}'
    r = cliente_api.put(RUTA, content=cuerpo, headers={**ADM, "Content-Type": "application/json"})
    assert_error(r, 422, "temperatura: debe ser un número finito")


@pytest.mark.parametrize("temperatura", [0, 0.0, 0.2])
def test_put_temperatura_en_los_limites_200(cliente_api, temperatura):
    r = poner(cliente_api, {**VALIDO, "temperatura": temperatura})
    assert r.status_code == 200, r.text
    assert r.json()["temperatura"] == pytest.approx(temperatura)


@pytest.mark.parametrize(
    "extra",
    [
        {"gemini_api_key": CLAVE_GEMINI},
        {"openai_compat_api_key": CLAVE_OPENAI},
        {"base_url": URL_PRIVADA},
        {"versiones_prompt": {"evaluar_laboratorio": "9.9"}},
        {"motivo": "porque sí"},
        {"actualizado_por": str(ID_DOCENTE)},
    ],
    ids=["gemini_key", "openai_key", "base_url", "prompts", "motivo", "actualizado_por"],
)
def test_put_campos_no_permitidos_422_sin_eco(cliente_api, fabrica_api, extra):
    r = poner(cliente_api, {**VALIDO, **extra})
    campo = next(iter(extra))
    assert_error(r, 422, f"{campo}: no se permite este campo")
    for valor in (CLAVE_GEMINI, CLAVE_OPENAI, URL_PRIVADA, "llm.ejemplo.com", "9.9", "porque"):
        assert valor not in r.text
    assert fila(fabrica_api) is None and auditorias(fabrica_api) == []


@pytest.mark.parametrize("faltante", ["proveedor", "modelo", "temperatura"])
def test_put_campo_faltante_422(cliente_api, faltante):
    cuerpo = {k: v for k, v in VALIDO.items() if k != faltante}
    assert_error(poner(cliente_api, cuerpo), 422, f"{faltante}: es obligatorio")


def test_put_sin_cuerpo_422(cliente_api):
    assert_error(cliente_api.put(RUTA, headers=ADM), 422)


def test_put_falla_auditoria_no_guarda_cambio(fabrica_api, monkeypatch):
    """El cambio y la auditoría van en la misma transacción: si una falla, no queda nada."""
    crear_fila(fabrica_api)
    monkeypatch.setattr(servicio, "ENTIDAD_AUDITORIA", None)
    with fabrica_api() as s:
        actor = s.get(Perfil, ID_ADMIN)
        with pytest.raises(IntegrityError):
            servicio.cambiar_config(s, actor, "gemini", "gemini-2.5-flash", 0.05, ajustes())
    guardada = fila(fabrica_api)
    assert (guardada.modelo, guardada.temperatura) == ("gemini-3.5-flash-lite", 0.1)
    assert auditorias(fabrica_api) == []


def test_put_cambia_la_config_que_usan_las_evaluaciones(cliente_api, fabrica_api):
    usar_ajustes(cliente_api, openai_compat_modelos="llama3.1:8b")
    poner(cliente_api, {"proveedor": "openai_compat", "modelo": "llama3.1:8b", "temperatura": 0.2})
    with fabrica_api() as s:
        config = configuracion_ia(s, ajustes())
    assert (config.proveedor, config.modelo) == ("openai_compat", "llama3.1:8b")
    assert config.temperatura == pytest.approx(0.2)
