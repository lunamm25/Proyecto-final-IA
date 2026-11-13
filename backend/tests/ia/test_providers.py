"""Tests de los proveedores de LLM usando solo FakeProvider (sin gastar API)."""

import pytest
from pydantic import BaseModel

from app.ia.providers import (
    ErrorConfiguracionLLM,
    ErrorRespuestaLLM,
    FakeProvider,
    obtener_proveedor,
)


class Respuesta(BaseModel):
    """Esquema pequeño para los tests."""

    respuesta: str
    confianza: float


def test_respuesta_valida_se_devuelve_validada() -> None:
    proveedor = FakeProvider([{"respuesta": "hola", "confianza": 0.9}])
    resultado = proveedor.generar_json("pregunta", Respuesta)
    assert resultado == Respuesta(respuesta="hola", confianza=0.9)
    assert len(proveedor.prompts_recibidos) == 1
    assert proveedor.ultima_respuesta_cruda is not None


def test_respuesta_invalida_reintenta_con_error() -> None:
    proveedor = FakeProvider(
        [
            '{"respuesta": "hola"}',
            Respuesta(respuesta="hola", confianza=0.5),
        ]
    )
    resultado = proveedor.generar_json("pregunta original", Respuesta)
    assert resultado.confianza == 0.5
    assert len(proveedor.prompts_recibidos) == 2
    segundo = proveedor.prompts_recibidos[1]
    assert "pregunta original" in segundo
    assert "confianza" in segundo
    assert "Error de validación" in segundo
    assert '{"respuesta": "hola"}' in segundo


def test_json_malformado_tambien_reintenta() -> None:
    proveedor = FakeProvider(["esto no es json", {"respuesta": "ok", "confianza": 1}])
    assert proveedor.generar_json("p", Respuesta).respuesta == "ok"
    assert len(proveedor.prompts_recibidos) == 2


def test_tres_respuestas_invalidas_lanzan_error() -> None:
    proveedor = FakeProvider(["{}", "{}", "{}", {"respuesta": "tarde", "confianza": 1}])
    with pytest.raises(ErrorRespuestaLLM, match="3 intentos"):
        proveedor.generar_json("p", Respuesta)
    assert len(proveedor.prompts_recibidos) == 3


def test_obtener_proveedor_limita_temperatura(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.9")
    proveedor = obtener_proveedor()
    assert isinstance(proveedor, FakeProvider)
    assert proveedor.temperatura == 0.2


def test_obtener_proveedor_desconocido_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "inventado")
    with pytest.raises(ErrorConfiguracionLLM, match="desconocido"):
        obtener_proveedor()


def test_obtener_proveedor_gemini_sin_clave_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    with pytest.raises(ErrorConfiguracionLLM, match="GEMINI_API_KEY"):
        obtener_proveedor()


def test_obtener_proveedor_temperatura_invalida(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_TEMPERATURE", "alta")
    with pytest.raises(ErrorConfiguracionLLM, match="LLM_TEMPERATURE"):
        obtener_proveedor()
