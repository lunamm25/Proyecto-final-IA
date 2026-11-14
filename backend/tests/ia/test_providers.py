"""Tests de los proveedores de LLM usando solo FakeProvider (sin gastar API)."""

import sys
import types
from typing import Any

import pytest
from pydantic import BaseModel

from app.ia.providers import (
    MAX_REINTENTOS,
    ErrorConfiguracionLLM,
    ErrorRespuestaLLM,
    FakeProvider,
    GeminiProvider,
    OpenAICompatProvider,
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


# --- max_retries configurable (clientes SDK simulados, sin red) ---


class _ClienteOpenAIFalso:
    """Imita openai.OpenAI: cuenta llamadas y siempre devuelve JSON inválido."""

    def __init__(self, **_: Any) -> None:
        self.llamadas = 0
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._crear)
        )

    def _crear(self, **_: Any) -> Any:
        self.llamadas += 1
        mensaje = types.SimpleNamespace(content="{}")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=mensaje)])


class _ClienteGeminiFalso:
    """Imita google.genai.Client: cuenta llamadas y siempre devuelve JSON inválido."""

    def __init__(self, **_: Any) -> None:
        self.llamadas = 0
        self.models = types.SimpleNamespace(generate_content=self._generar)

    def _generar(self, **_: Any) -> Any:
        self.llamadas += 1
        return types.SimpleNamespace(text="{}")


@pytest.fixture
def openai_falso(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reemplaza el módulo openai por uno falso para no tocar la red."""
    modulo = types.ModuleType("openai")
    modulo.OpenAI = _ClienteOpenAIFalso  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", modulo)


@pytest.fixture
def gemini_falso(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reemplaza google.genai por un módulo falso para no tocar la red."""
    tipos = types.ModuleType("google.genai.types")
    tipos.HttpOptions = lambda **kw: kw  # type: ignore[attr-defined]
    tipos.GenerateContentConfig = lambda **kw: kw  # type: ignore[attr-defined]
    genai = types.ModuleType("google.genai")
    genai.Client = _ClienteGeminiFalso  # type: ignore[attr-defined]
    genai.types = tipos  # type: ignore[attr-defined]
    google = types.ModuleType("google")
    google.genai = genai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", tipos)


def _openai(**kwargs: Any) -> OpenAICompatProvider:
    return OpenAICompatProvider(base_url="http://falso/v1", api_key="x", modelo="m", **kwargs)


def _gemini(**kwargs: Any) -> GeminiProvider:
    return GeminiProvider(api_key="x", **kwargs)


@pytest.mark.usefixtures("openai_falso")
def test_openai_max_retries_por_defecto_hace_tres_intentos() -> None:
    proveedor = _openai()
    assert proveedor.max_retries == MAX_REINTENTOS == 2
    with pytest.raises(ErrorRespuestaLLM, match="3 intentos"):
        proveedor.generar_json("p", Respuesta)
    assert proveedor._client.llamadas == 3


@pytest.mark.usefixtures("openai_falso")
def test_openai_max_retries_cero_hace_un_intento() -> None:
    proveedor = _openai(max_retries=0)
    with pytest.raises(ErrorRespuestaLLM, match="1 intentos"):
        proveedor.generar_json("p", Respuesta)
    assert proveedor._client.llamadas == 1


@pytest.mark.usefixtures("openai_falso")
def test_openai_max_retries_mayor_a_dos_se_recorta() -> None:
    proveedor = _openai(max_retries=5)
    assert proveedor.max_retries == 2
    with pytest.raises(ErrorRespuestaLLM):
        proveedor.generar_json("p", Respuesta)
    assert proveedor._client.llamadas == 3


@pytest.mark.usefixtures("openai_falso")
def test_openai_max_retries_negativo_falla() -> None:
    with pytest.raises(ErrorConfiguracionLLM, match="max_retries no puede ser negativo"):
        _openai(max_retries=-1)


@pytest.mark.usefixtures("gemini_falso")
def test_gemini_max_retries_por_defecto_hace_tres_intentos() -> None:
    proveedor = _gemini()
    assert proveedor.max_retries == 2
    with pytest.raises(ErrorRespuestaLLM, match="3 intentos"):
        proveedor.generar_json("p", Respuesta)
    assert proveedor._client.llamadas == 3


@pytest.mark.usefixtures("gemini_falso")
def test_gemini_max_retries_cero_y_recorte() -> None:
    proveedor = _gemini(max_retries=0)
    with pytest.raises(ErrorRespuestaLLM):
        proveedor.generar_json("p", Respuesta)
    assert proveedor._client.llamadas == 1
    assert _gemini(max_retries=5).max_retries == 2


@pytest.mark.usefixtures("gemini_falso")
def test_gemini_max_retries_negativo_falla() -> None:
    with pytest.raises(ErrorConfiguracionLLM, match="max_retries no puede ser negativo"):
        _gemini(max_retries=-3)


@pytest.mark.usefixtures("openai_falso")
def test_obtener_proveedor_openai_usa_reintentos_por_defecto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compat")
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "m")
    proveedor = obtener_proveedor()
    assert isinstance(proveedor, OpenAICompatProvider)
    assert proveedor.max_retries == 2


def test_fake_provider_conserva_reintentos_por_defecto() -> None:
    assert FakeProvider([]).max_retries == MAX_REINTENTOS
