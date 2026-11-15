"""Pruebas del tachado de secretos compartido y de su uso en auditoría y en /traza."""

import json

from app.config import get_settings
from app.models import Auditoria
from app.services import secretos
from app.services.evaluador_ia import EvaluacionIAError
from app.services.informe_ia import GeneracionIAError, detalle_error
from tests.test_auth import ID_DOCENTE, ajustes
from tests.test_evaluaciones import auditorias, auth, evaluar

# Valor exacto de una clave de Settings que no encaja con ningún patrón conocido.
CLAVE_EXACTA = "clave-de-servicio-inventada-QUE-NO-DEBE-SALIR-987"
TEXTO_SENSIBLE = (
    "Fallo al llamar a https://usuario:clave@host.example/v1/modelos?key=AIzaSyFALSA_123-x "
    "con Authorization: Bearer eyJhbGciOi.eyJzdWIi.firma usando " + CLAVE_EXACTA
)
FRAGMENTOS_PROHIBIDOS = ("usuario:clave", "AIzaSyFALSA", "eyJhbGciOi", CLAVE_EXACTA)


def settings_con_clave():
    """Settings inventados cuya clave de Gemini es CLAVE_EXACTA."""
    return ajustes(gemini_api_key=CLAVE_EXACTA)


def sin_fragmentos(texto: str) -> None:
    """Comprueba que ningún dato sensible aparece en el texto."""
    for fragmento in FRAGMENTOS_PROHIBIDOS:
        assert fragmento not in texto, fragmento


# ---------- Módulo compartido ----------


def test_tachar_sin_recortar_tacha_todo_y_no_recorta():
    texto = TEXTO_SENSIBLE + " " + "x" * 5000
    tachado = secretos.tachar_sin_recortar(texto, settings_con_clave())
    sin_fragmentos(tachado)
    assert tachado.endswith("x" * 5000)


def test_tachar_secretos_sigue_recortando():
    tachado = secretos.tachar_secretos(TEXTO_SENSIBLE + "x" * 5000, settings_con_clave())
    sin_fragmentos(tachado)
    assert len(tachado) <= secretos.LIMITE_MENSAJE_ERROR


def test_tachar_credenciales_respeta_texto_normal():
    normal = (
        "El estudiante cita https://docs.python.org/3/library/re.html y usa key: valor.\n"
        "Nota parcial 3,5; función sk_learn() y token de 12 caracteres."
    )
    assert secretos.tachar_credenciales(normal, settings_con_clave()) == normal


def test_tachar_credenciales_tacha_credenciales():
    tachado = secretos.tachar_credenciales(TEXTO_SENSIBLE, settings_con_clave())
    sin_fragmentos(tachado)
    assert "https://***@host.example/v1/modelos?key=***" in tachado
    assert "Bearer ***" in tachado


def test_tachar_en_estructura_recorre_dict_y_listas():
    datos = {"a": [TEXTO_SENSIBLE, {"b": TEXTO_SENSIBLE}], "n": 3, "ok": True, "nada": None}
    limpio = secretos.tachar_en_estructura(
        datos, lambda t: secretos.tachar_credenciales(t, settings_con_clave())
    )
    sin_fragmentos(json.dumps(limpio))
    assert (limpio["n"], limpio["ok"], limpio["nada"]) == (3, True, None)


def test_config_ia_reutiliza_el_modulo_compartido():
    from app.services import almacen, config_ia, entregas

    assert config_ia.tachar_secretos is secretos.tachar_secretos
    assert almacen.tachar_secretos is secretos.tachar_secretos
    assert entregas.tachar_secretos is secretos.tachar_secretos


# ---------- Detalle de errores de IA ----------


def _error_con_causa(clase):
    """Error de IA con mensaje, errores, crudas y causa llenos de datos sensibles."""
    try:
        try:
            raise RuntimeError(TEXTO_SENSIBLE)
        except RuntimeError as causa:
            raise clase(
                TEXTO_SENSIBLE,
                errores=[TEXTO_SENSIBLE, "campo nivel: obligatorio"],
                respuestas_crudas=['{"respuesta": "' + TEXTO_SENSIBLE + '"}'],
            ) from causa
    except clase as error:
        return error


def test_detalle_error_informe_tacha_todo():
    detalle = detalle_error(_error_con_causa(GeneracionIAError), settings_con_clave())
    sin_fragmentos(json.dumps(detalle, ensure_ascii=False))
    assert detalle["errores"][1] == "campo nivel: obligatorio"
    assert "***" in detalle["mensaje"] and "***" in detalle["causa"]


def test_detalle_error_informe_usa_settings_por_defecto(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("GEMINI_API_KEY", CLAVE_EXACTA)
    try:
        detalle = detalle_error(_error_con_causa(GeneracionIAError))
    finally:
        get_settings.cache_clear()
    sin_fragmentos(json.dumps(detalle, ensure_ascii=False))


def test_error_de_evaluacion_queda_tachado_en_auditoria_y_traza(cliente, datos, evaluador):
    cliente.app.dependency_overrides[get_settings] = settings_con_clave
    evaluador.excepcion = _error_con_causa(EvaluacionIAError)
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    filas = [a for a in auditorias(datos, evaluacion_id) if a.accion == "evaluacion_ia_error"]
    assert len(filas) == 1
    guardado = json.dumps(filas[0].despues, ensure_ascii=False)
    sin_fragmentos(guardado)
    assert "***" in filas[0].despues["mensaje"]
    assert "***" in filas[0].despues["causa"]
    assert all("***" in e for e in filas[0].despues["errores"][:1])
    r = cliente.get(f"/api/evaluaciones/{evaluacion_id}/traza", headers=auth(ID_DOCENTE))
    assert r.status_code == 200
    sin_fragmentos(r.text)


# ---------- Segunda capa en /traza ----------


def test_traza_tacha_valores_sensibles_sin_alterar_texto_normal(cliente, datos, evaluador):
    cliente.app.dependency_overrides[get_settings] = settings_con_clave
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    normal = "Respuesta larga del modelo con https://docs.python.org y nivel 3,5. " * 200
    with datos() as s:
        s.add(
            Auditoria(
                entidad="evaluaciones",
                entidad_id=str(evaluacion_id),
                accion="prueba_valores",
                despues={"detalle": TEXTO_SENSIBLE, "crudas": [normal], "n": 7},
            )
        )
        s.commit()
    r = cliente.get(f"/api/evaluaciones/{evaluacion_id}/traza", headers=auth(ID_DOCENTE))
    assert r.status_code == 200
    sin_fragmentos(r.text)
    evento = next(e for e in r.json()["eventos"] if e["accion"] == "prueba_valores")
    assert evento["despues"]["crudas"] == [normal]
    assert evento["despues"]["n"] == 7

