"""Pruebas de la configuración de IA (RF-10): GET/PUT/probar /api/config-ia, solo admin."""

import json
import sys
import time

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api import deps
from app.config import get_settings
from app.models import Auditoria, ConfigIA, Perfil
from app.services import config_ia as servicio
from app.services import evaluador_ia
from app.services.evaluaciones import ConfigEvaluacion, configuracion_ia
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
VALIDO = {"proveedor": "gemini", "modelo": "gemini-3.6-flash", "temperatura": 0.05}


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
    crear_fila(fabrica_api, modelo="gemini-3.6-flash", temperatura=0.15)
    datos = cliente_api.get(RUTA, headers=ADM).json()
    assert (datos["proveedor"], datos["modelo"]) == ("gemini", "gemini-3.6-flash")
    assert datos["temperatura"] == pytest.approx(0.15)
    assert datos["origen"] == "base_de_datos"
    assert datos["modelo_permitido"] is True
    assert datos["actualizado_por"] == {"id": str(ID_ADMIN), "nombre": "Alba Admin"}
    assert datos["actualizado_en"]
    assert datos["temperatura_maxima"] == pytest.approx(0.2)


def test_get_sin_fila_usa_settings(cliente_api):
    usar_ajustes(cliente_api, llm_provider="gemini", llm_model="gemini-3.6-flash")
    datos = cliente_api.get(RUTA, headers=ADM).json()
    assert datos["origen"] == "entorno"
    assert (datos["proveedor"], datos["modelo"]) == ("gemini", "gemini-3.6-flash")
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
    assert proveedores[0]["modelos"] == ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
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


def test_modelos_probados_por_proveedor(cliente_api):
    usar_ajustes(cliente_api, openai_compat_modelos="llama3.1:8b")
    proveedores = cliente_api.get(RUTA, headers=ADM).json()["proveedores_permitidos"]
    assert all(
        set(p) == {"proveedor", "etiqueta", "modelos", "modelos_probados"} for p in proveedores
    )
    assert all(isinstance(m, str) for p in proveedores for m in p["modelos"])
    assert proveedores[0]["modelos_probados"] == ["gemini-3.5-flash-lite"]
    assert proveedores[1]["modelos_probados"] == []


def test_modelos_probados_solo_si_estan_permitidos(cliente_api, monkeypatch):
    monkeypatch.setattr(
        servicio,
        "MODELOS_PROBADOS",
        {
            "gemini": ("gemini-3.5-flash-lite", "gemini-x-no-permitido"),
            "openai_compat": ("llama3",),
        },
    )
    proveedores = cliente_api.get(RUTA, headers=ADM).json()["proveedores_permitidos"]
    assert proveedores[0]["modelos_probados"] == ["gemini-3.5-flash-lite"]
    assert proveedores[1]["modelos_probados"] == []


def test_put_gemini_25_flash_retirado_422(cliente_api, fabrica_api):
    r = poner(cliente_api, {**VALIDO, "modelo": "gemini-2.5-flash"})
    assert_error(
        r,
        422,
        "Modelo no permitido para gemini. Opciones: gemini-3.5-flash-lite, gemini-3.6-flash.",
    )
    assert fila(fabrica_api) is None and auditorias(fabrica_api) == []


def test_fila_guardada_con_modelo_retirado_no_falla(cliente_api, fabrica_api):
    crear_fila(fabrica_api, modelo="gemini-2.5-flash")
    r = cliente_api.get(RUTA, headers=ADM)
    assert r.status_code == 200, r.text
    assert r.json()["modelo"] == "gemini-2.5-flash"
    assert r.json()["modelo_permitido"] is False


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
    assert (datos["proveedor"], datos["modelo"]) == ("gemini", "gemini-3.6-flash")
    assert datos["temperatura"] == pytest.approx(0.05)
    assert datos["origen"] == "base_de_datos" and datos["modelo_permitido"] is True
    assert datos["actualizado_por"]["id"] == str(ID_ADMIN)
    guardada = fila(fabrica_api)
    assert (guardada.modelo, guardada.temperatura) == ("gemini-3.6-flash", pytest.approx(0.05))
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
        "modelo": "gemini-3.6-flash",
        "temperatura": 0.05,
    }
    assert registro.motivo is None


def test_put_actualiza_quien_lo_cambio(cliente_api, fabrica_api):
    with fabrica_api() as s:
        s.add(ConfigIA(id=1, proveedor="gemini", modelo="gemini-3.6-flash", temperatura=0.1))
        s.commit()
    poner(cliente_api, VALIDO)
    assert fila(fabrica_api).actualizado_por == ID_ADMIN


def test_put_mismo_valor_200_sin_auditoria(cliente_api, fabrica_api):
    crear_fila(fabrica_api, modelo="gemini-3.6-flash", temperatura=0.05)
    antes = fila(fabrica_api).actualizado_en
    r = poner(
        cliente_api, {"proveedor": " gemini ", "modelo": " gemini-3.6-flash ", "temperatura": 0.05}
    )
    assert r.status_code == 200, r.text
    assert r.json()["modelo"] == "gemini-3.6-flash"
    assert auditorias(fabrica_api) == []
    assert fila(fabrica_api).actualizado_en == antes


def test_primer_put_crea_fila_y_audita_origen_entorno(cliente_api, fabrica_api):
    usar_ajustes(cliente_api, llm_provider="gemini", llm_model="gemini-3.6-flash")
    r = poner(
        cliente_api, {"proveedor": "gemini", "modelo": "gemini-3.6-flash", "temperatura": 0.1}
    )
    assert r.status_code == 200, r.text
    assert r.json()["origen"] == "base_de_datos"
    guardada = fila(fabrica_api)
    assert (guardada.proveedor, guardada.modelo) == ("gemini", "gemini-3.6-flash")
    assert guardada.actualizado_por == ID_ADMIN
    [registro] = auditorias(fabrica_api)
    assert registro.accion == "cambiar_config_ia"
    assert registro.antes == {
        "origen": "entorno",
        "proveedor": "gemini",
        "modelo": "gemini-3.6-flash",
        "temperatura": 0.1,
    }
    assert registro.despues == {
        "proveedor": "gemini",
        "modelo": "gemini-3.6-flash",
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
    ["gemini 2.5", "gemini-3.6-flash\nX", "a" * 101, "", "-empieza-mal", "x;rm -rf"],
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
    cuerpo = b'{"proveedor": "gemini", "modelo": "gemini-3.6-flash", "temperatura": NaN}'
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
            servicio.cambiar_config(s, actor, "gemini", "gemini-3.6-flash", 0.05, ajustes())
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


# ---------- POST /api/config-ia/probar (RF-10 CA2) ----------

RUTA_PROBAR = "/api/config-ia/probar"
MSG_OK = "Conexión correcta con el proveedor de IA."
MSG_FALLO = "No se pudo conectar con el proveedor de IA. Revisa la configuración del servidor."
MSG_SIN_CLAVE = "Falta configurar la clave del proveedor en el servidor."
CAMPOS_PRUEBA = {"ok", "proveedor", "modelo", "latencia_ms", "mensaje"}
CLAVE_SB = "sb_secret_INVENTADA_789"


class ProbadorFalso:
    """Probador de conexión de prueba: registra llamadas y hace lo que se le indique."""

    def __init__(self, error: Exception | None = None, espera: float = 0.0) -> None:
        self.error = error
        self.espera = espera
        self.llamadas: list[tuple] = []

    def __call__(self, config, settings, timeout: float) -> None:
        self.llamadas.append((config.proveedor, config.modelo, config.temperatura, timeout))
        if self.espera:
            time.sleep(self.espera)
        if self.error is not None:
            raise self.error


def usar_probador(cliente, probador, limite: float | None = None) -> None:
    """Sustituye el probador real (y opcionalmente el límite de tiempo) por los de prueba."""
    cliente.app.dependency_overrides[deps.obtener_probador] = lambda: probador
    if limite is not None:
        cliente.app.dependency_overrides[deps.obtener_limite_prueba_ia] = lambda: limite


def probar(cliente, headers=ADM):
    """POST /api/config-ia/probar."""
    return cliente.post(RUTA_PROBAR, headers=headers)


def auditorias_prueba(fabrica) -> list[Auditoria]:
    """Filas de auditoría de pruebas de conexión."""
    return [a for a in auditorias(fabrica) if a.accion == "probar_config_ia"]


def texto_auditoria(fabrica) -> str:
    """antes/despues/motivo de toda la auditoría como texto (para buscar secretos)."""
    filas = auditorias(fabrica)
    return json.dumps([[a.antes, a.despues, a.motivo] for a in filas], ensure_ascii=False)


def test_probar_sin_token_401(cliente_api, fabrica_api):
    usar_probador(cliente_api, ProbadorFalso())
    assert_error(cliente_api.post(RUTA_PROBAR), 401)
    assert auditorias(fabrica_api) == []


@pytest.mark.parametrize("headers", [EST, DOC], ids=["estudiante", "docente"])
def test_probar_no_admin_403(cliente_api, fabrica_api, headers):
    probador = ProbadorFalso()
    usar_probador(cliente_api, probador)
    assert_error(probar(cliente_api, headers), 403)
    assert probador.llamadas == [] and auditorias(fabrica_api) == []


def test_probar_exito_200_y_audita(cliente_api, fabrica_api):
    usar_ajustes(cliente_api, gemini_api_key=CLAVE_GEMINI)
    probador = ProbadorFalso()
    usar_probador(cliente_api, probador, limite=2.5)
    r = probar(cliente_api)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert set(datos) == CAMPOS_PRUEBA
    assert datos["ok"] is True and datos["mensaje"] == MSG_OK
    assert (datos["proveedor"], datos["modelo"]) == ("gemini", "gemini-3.5-flash-lite")
    assert isinstance(datos["latencia_ms"], int) and datos["latencia_ms"] >= 0
    assert probador.llamadas == [("gemini", "gemini-3.5-flash-lite", 0.1, 2.5)]
    [registro] = auditorias_prueba(fabrica_api)
    assert registro.usuario_id == ID_ADMIN
    assert (registro.entidad, registro.entidad_id) == ("config_ia", "1")
    assert registro.antes is None and registro.motivo is None
    assert registro.despues == {
        "ok": True,
        "proveedor": "gemini",
        "modelo": "gemini-3.5-flash-lite",
        "latencia_ms": datos["latencia_ms"],
        "resultado": "ok",
        "error": None,
    }
    assert CLAVE_GEMINI not in r.text and CLAVE_GEMINI not in texto_auditoria(fabrica_api)


def test_probar_usa_la_configuracion_guardada(cliente_api, fabrica_api):
    crear_fila(fabrica_api, modelo="gemini-3.6-flash", temperatura=0.05)
    usar_ajustes(cliente_api, gemini_api_key=CLAVE_GEMINI)
    probador = ProbadorFalso()
    usar_probador(cliente_api, probador)
    datos = probar(cliente_api).json()
    assert datos["modelo"] == "gemini-3.6-flash"
    assert probador.llamadas == [("gemini", "gemini-3.6-flash", 0.05, 10.0)]


def test_probar_no_cambia_la_configuracion(cliente_api, fabrica_api):
    crear_fila(fabrica_api)
    usar_ajustes(cliente_api, gemini_api_key=CLAVE_GEMINI)
    usar_probador(cliente_api, ProbadorFalso(error=RuntimeError("caído")))
    probar(cliente_api)
    guardada = fila(fabrica_api)
    assert (guardada.proveedor, guardada.modelo, guardada.temperatura) == (
        "gemini",
        "gemini-3.5-flash-lite",
        0.1,
    )
    assert [a.accion for a in auditorias(fabrica_api)] == ["probar_config_ia"]


def test_probar_fallo_mensaje_generico_y_detalle_tachado(cliente_api, fabrica_api):
    usar_ajustes(
        cliente_api,
        gemini_api_key=CLAVE_GEMINI,
        openai_compat_api_key=CLAVE_OPENAI,
        openai_compat_base_url=URL_PRIVADA,
    )
    jwt_falso = token_hs(ID_ADMIN)
    crudo = (
        f"Fallo con clave {CLAVE_GEMINI} y {CLAVE_OPENAI} en {URL_PRIVADA}; "
        f"Authorization: Bearer abc.def.ghi; token {jwt_falso}; {CLAVE_SB}; "
        "url=http://127.0.0.1:9/v1/chat?api_key=xyz987&token=tok654 key=k321"
    )
    usar_probador(cliente_api, ProbadorFalso(error=RuntimeError(crudo)))
    r = probar(cliente_api)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["ok"] is False and datos["mensaje"] == MSG_FALLO
    assert isinstance(datos["latencia_ms"], int)
    [registro] = auditorias_prueba(fabrica_api)
    assert registro.despues["resultado"] == "fallo"
    assert registro.despues["error"]["tipo"] == "RuntimeError"
    mensaje = registro.despues["error"]["mensaje"]
    assert mensaje.startswith("Fallo con clave ***")
    secretos = [
        CLAVE_GEMINI,
        CLAVE_OPENAI,
        URL_PRIVADA,
        "contrasena",
        "llm.ejemplo.com",
        "abc.def.ghi",
        jwt_falso,
        jwt_falso[:20],
        CLAVE_SB,
        "127.0.0.1:9",
        "xyz987",
        "tok654",
        "k321",
    ]
    for secreto in secretos:
        assert secreto not in r.text, secreto
        assert secreto not in texto_auditoria(fabrica_api), secreto


def test_probar_tiempo_agotado_no_espera_al_proveedor(cliente_api, fabrica_api):
    usar_ajustes(cliente_api, gemini_api_key=CLAVE_GEMINI)
    usar_probador(cliente_api, ProbadorFalso(espera=1.0), limite=0.05)
    inicio = time.monotonic()
    r = probar(cliente_api)
    assert time.monotonic() - inicio < 0.8
    datos = r.json()
    assert r.status_code == 200 and datos["ok"] is False
    assert datos["mensaje"].startswith("El proveedor de IA no respondió a tiempo")
    assert datos["latencia_ms"] == 50
    [registro] = auditorias_prueba(fabrica_api)
    assert registro.despues["resultado"] == "tiempo_agotado"
    assert registro.despues["latencia_ms"] == 50
    assert registro.despues["error"]["tipo"] == "TimeoutError"


def test_probar_tiempo_agotado_mensaje_con_el_limite_real(cliente_api):
    usar_ajustes(cliente_api, gemini_api_key=CLAVE_GEMINI)
    usar_probador(cliente_api, ProbadorFalso(espera=0.5), limite=0.01)
    assert probar(cliente_api).json()["mensaje"] == (
        "El proveedor de IA no respondió a tiempo (0.01 s)."
    )


def test_limite_por_defecto_es_10_segundos():
    assert deps.obtener_limite_prueba_ia() == 10.0
    assert servicio.mensaje_tiempo_agotado(10.0) == (
        "El proveedor de IA no respondió a tiempo (10 s)."
    )


def test_probar_gemini_sin_clave_no_llama(cliente_api, fabrica_api):
    probador = ProbadorFalso()
    usar_probador(cliente_api, probador)
    datos = probar(cliente_api).json()
    assert datos == {
        "ok": False,
        "proveedor": "gemini",
        "modelo": "gemini-3.5-flash-lite",
        "latencia_ms": None,
        "mensaje": MSG_SIN_CLAVE,
    }
    assert probador.llamadas == []
    [registro] = auditorias_prueba(fabrica_api)
    assert registro.despues["resultado"] == "sin_clave"
    assert registro.despues["latencia_ms"] is None


def test_probar_openai_remoto_sin_clave(cliente_api, fabrica_api):
    crear_fila(fabrica_api, proveedor="openai_compat", modelo="llama3")
    usar_ajustes(cliente_api, openai_compat_base_url="https://api.groq.com/openai/v1")
    probador = ProbadorFalso()
    usar_probador(cliente_api, probador)
    r = probar(cliente_api)
    assert r.json()["mensaje"] == MSG_SIN_CLAVE and probador.llamadas == []
    assert "groq" not in r.text and "groq" not in texto_auditoria(fabrica_api)


@pytest.mark.parametrize("url", ["", "http://localhost:11434/v1", "http://127.0.0.1:9/v1"])
def test_probar_openai_local_no_necesita_clave(cliente_api, fabrica_api, url):
    crear_fila(fabrica_api, proveedor="openai_compat", modelo="llama3")
    usar_ajustes(cliente_api, openai_compat_base_url=url)
    probador = ProbadorFalso()
    usar_probador(cliente_api, probador)
    assert probar(cliente_api).json()["ok"] is True
    assert len(probador.llamadas) == 1


def test_probar_error_de_configuracion_del_proveedor_es_sin_clave(cliente_api, fabrica_api):
    usar_ajustes(cliente_api, gemini_api_key=CLAVE_GEMINI)
    error = evaluador_ia.ProveedorSinConfigurarError(f"Falta algo: {CLAVE_GEMINI}")
    usar_probador(cliente_api, ProbadorFalso(error=error))
    r = probar(cliente_api)
    assert r.json()["mensaje"] == MSG_SIN_CLAVE and r.json()["latencia_ms"] is None
    [registro] = auditorias_prueba(fabrica_api)
    assert registro.despues["resultado"] == "sin_clave"
    assert CLAVE_GEMINI not in texto_auditoria(fabrica_api)


def test_probar_no_importa_modulos_de_ia(cliente_api, monkeypatch):
    for nombre in [m for m in sys.modules if m == "app.ia" or m.startswith("app.ia.")]:
        monkeypatch.delitem(sys.modules, nombre)
    usar_ajustes(cliente_api, gemini_api_key=CLAVE_GEMINI)
    usar_probador(cliente_api, ProbadorFalso())
    assert probar(cliente_api).json()["ok"] is True
    assert "app.ia.evaluador" not in sys.modules
    assert not [m for m in sys.modules if m == "app.ia" or m.startswith("app.ia.")]


# ---------- Tachado de secretos ----------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("ver https://u:p@host.com/x?y=1 ya", "ver *** ya"),
        ("Authorization: Bearer abc123", "Authorization: Bearer ***"),
        ("clave sk-abcDEF123_x fin", "clave *** fin"),
        ("clave AIzaSyFALSA_123-x fin", "clave *** fin"),
        (f"clave {CLAVE_SB} fin", "clave *** fin"),
        ("jwt eyJhbGciOi.eyJzdWIi.firma fin", "jwt *** fin"),
        ("api_key=123 key=456 token=789 KEY=000", "api_key=*** key=*** token=*** KEY=***"),
        ("postgresql://user:pass@db:5432/x", "***"),
        ("sin secretos", "sin secretos"),
    ],
)
def test_tachar_patrones(texto, esperado):
    assert servicio.tachar_secretos(texto, ajustes()) == esperado


def test_tachar_valores_exactos_de_settings():
    settings = ajustes(
        gemini_api_key="valor-gemini-raro",
        openai_compat_api_key="otra-clave",
        openai_compat_base_url="mi-servidor.interno:8080",
    )
    texto = "valor-gemini-raro / otra-clave / mi-servidor.interno:8080"
    assert servicio.tachar_secretos(texto, settings) == "*** / *** / ***"


def test_tachar_recorta_el_mensaje():
    tachado = servicio.tachar_secretos("x" * 5000, ajustes())
    assert len(tachado) <= servicio.LIMITE_MENSAJE_ERROR


# ---------- Probador real (sin red: el proveedor se sustituye) ----------


class ProveedorDePrueba:
    """Proveedor sustituto que registra las llamadas (sin red)."""

    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def generar_json(self, prompt, schema, imagenes=None):
        self.llamadas.append("generar_json")
        return schema(ok=True)


class ProveedorConTexto(ProveedorDePrueba):
    """Proveedor sustituto con `generar_texto` (una sola llamada, versión de rol1-ia)."""

    def generar_texto(self, prompt, schema, imagenes=None):
        self.llamadas.append("generar_texto")
        return '{"ok": true}'


@pytest.mark.parametrize(
    ("clase", "metodo"),
    [(ProveedorDePrueba, "generar_json"), (ProveedorConTexto, "generar_texto")],
)
def test_probador_real_hace_una_sola_llamada(monkeypatch, clase, metodo):
    proveedor = clase()
    recibidos = {}

    def construir(config, settings, timeout=None):
        recibidos["timeout"] = timeout
        return proveedor

    monkeypatch.setattr(evaluador_ia, "construir_proveedor", construir)
    config = ConfigEvaluacion("gemini", "gemini-3.5-flash-lite", 0.1)
    evaluador_ia.probar_conexion_ia(config, ajustes(), 7.0)
    assert proveedor.llamadas == [metodo]
    assert recibidos["timeout"] == 7.0


def test_probador_real_traduce_error_de_configuracion(monkeypatch):
    from app.ia.providers import ErrorConfiguracionLLM

    def construir(config, settings, timeout=None):
        raise ErrorConfiguracionLLM("Falta GEMINI_API_KEY para usar el proveedor Gemini.")

    monkeypatch.setattr(evaluador_ia, "construir_proveedor", construir)
    config = ConfigEvaluacion("gemini", "gemini-3.5-flash-lite", 0.1)
    with pytest.raises(evaluador_ia.ProveedorSinConfigurarError):
        evaluador_ia.probar_conexion_ia(config, ajustes(), 7.0)


def test_obtener_probador_por_defecto_es_el_real():
    assert deps.obtener_probador() is evaluador_ia.probar_conexion_ia


class ModuloProveedores:
    """Sustituto de `app.ia.providers` que registra los argumentos del constructor."""

    OLLAMA_BASE_URL = "http://localhost:11434/v1"

    def __init__(self) -> None:
        self.argumentos: dict = {}

    def GeminiProvider(self, **kwargs):  # noqa: N802  (imita el nombre de la clase)
        self.argumentos = kwargs
        return "proveedor"


def test_construir_proveedor_timeout_opcional(monkeypatch):
    modulo = ModuloProveedores()
    monkeypatch.setattr(evaluador_ia, "_importar", lambda _nombre: modulo)
    config = ConfigEvaluacion("gemini", "gemini-3.5-flash-lite", 0.1)
    evaluador_ia.construir_proveedor(config, ajustes(gemini_api_key="x"))
    assert "timeout" not in modulo.argumentos
    evaluador_ia.construir_proveedor(config, ajustes(gemini_api_key="x"), timeout=10.0)
    assert modulo.argumentos["timeout"] == 10.0
