"""Reintentos por errores transitorios del proveedor (503, 429, timeout) y LLM_MAX_RETRIES."""

import sys
import types
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from app.ia import comun
from app.ia.comun import PAUSAS_TRANSITORIAS
from app.ia.evaluador import ErrorEvaluacion, evaluar_laboratorio
from app.ia.informe import ErrorInforme, generar_informe_narrativo
from app.ia.providers import (
    ErrorConfiguracionLLM,
    ErrorRespuestaLLM,
    FakeProvider,
    es_error_transitorio,
    obtener_proveedor,
)
from app.ia.tematicas import ErrorMapeo, mapear_criterios_a_tematicas
from tests.ia import test_evaluador as te
from tests.ia import test_informe as ti
from tests.ia import test_tematicas as tt
from tests.ia.test_providers import (  # noqa: F401 - fixtures
    _gemini,
    _openai,
    gemini_falso,
    openai_falso,
)

ERROR_503 = ErrorRespuestaLLM("Error al llamar a Gemini (m): 503 UNAVAILABLE.", transitorio=True)
ERROR_400 = ErrorRespuestaLLM("Error al llamar a Gemini (m): 400 INVALID_ARGUMENT.")


class _Esquema(BaseModel):
    """Esquema mínimo para las llamadas directas al proveedor."""

    valor: int


class ProveedorConFallos(FakeProvider):
    """FakeProvider que lanza las excepciones que encuentre en su lista de respuestas."""

    def _llamar(self, prompt: str, schema: type[BaseModel], imagenes: list[bytes] | None) -> str:
        """Lanza la siguiente respuesta si es una excepción; si no, la devuelve como texto."""
        if self.respuestas and isinstance(self.respuestas[0], Exception):
            self.prompts_recibidos.append(prompt)
            raise self.respuestas.pop(0)
        return super()._llamar(prompt, schema, imagenes)


@pytest.fixture
def pausas(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Reemplaza la espera por una que solo anota los segundos pedidos."""
    registro: list[float] = []
    monkeypatch.setattr(comun, "_dormir", registro.append)
    return registro


def _evaluar(proveedor: FakeProvider) -> Any:
    """Llama al evaluador con el contexto de las pruebas del evaluador."""
    rubrica = te._rubrica()
    return evaluar_laboratorio(
        rubrica, "Lab", "Objetivo", te.INFORME, None, te.VERIFICACION, proveedor
    )


def _mapear(proveedor: FakeProvider) -> Any:
    """Llama al mapeo con las temáticas de las pruebas del mapeo."""
    return mapear_criterios_a_tematicas(tt._rubrica(), tt.TEMATICAS, proveedor)


def _informe(proveedor: FakeProvider) -> Any:
    """Llama a la narrativa con los datos de las pruebas del informe."""
    return generar_informe_narrativo(ti._datos(), proveedor)


FLUJOS = [
    pytest.param(_evaluar, lambda: te._respuesta(te._rubrica()), ErrorEvaluacion, id="evaluador"),
    pytest.param(_mapear, lambda: tt._respuesta(tt._rubrica()), ErrorMapeo, id="mapeo"),
    pytest.param(_informe, ti._respuesta, ErrorInforme, id="informe"),
]


@pytest.mark.parametrize(("flujo", "valida", "error_cls"), FLUJOS)
def test_503_una_vez_y_luego_exito(flujo, valida, error_cls, pausas: list[float]) -> None:
    """Un 503 seguido de una respuesta válida termina bien y sin errores de validación."""
    proveedor = ProveedorConFallos([ERROR_503, valida()])
    resultado = flujo(proveedor)
    assert resultado.intentos == 1
    assert resultado.errores_intentos == []
    assert pausas == [3.0]
    assert proveedor.prompts_recibidos[0] == proveedor.prompts_recibidos[1]


@pytest.mark.parametrize(("flujo", "valida", "error_cls"), FLUJOS)
def test_503_tres_veces_agota_y_falla(flujo, valida, error_cls, pausas: list[float]) -> None:
    """Tres 503 seguidos: 3 llamadas, pausas de 3 s y 8 s, y el error con el mensaje de hoy."""
    proveedor = ProveedorConFallos([ERROR_503] * 3 + [valida()])
    with pytest.raises(error_cls, match="Falló la llamada al proveedor de IA") as info:
        flujo(proveedor)
    assert len(proveedor.prompts_recibidos) == 3
    assert pausas == list(PAUSAS_TRANSITORIAS) == [3.0, 8.0]
    assert info.value.errores == []
    assert isinstance(info.value.__cause__, ErrorRespuestaLLM)


@pytest.mark.parametrize(("flujo", "valida", "error_cls"), FLUJOS)
def test_error_no_transitorio_falla_de_inmediato(
    flujo, valida, error_cls, pausas: list[float]
) -> None:
    """Un 400 (no transitorio) falla con una sola llamada y sin esperar."""
    proveedor = ProveedorConFallos([ERROR_400, valida()])
    with pytest.raises(error_cls, match="400"):
        flujo(proveedor)
    assert len(proveedor.prompts_recibidos) == 1
    assert pausas == []


@pytest.mark.parametrize(("flujo", "valida", "error_cls"), FLUJOS)
def test_contadores_transitorio_y_validacion_son_independientes(
    flujo, valida, error_cls, pausas: list[float]
) -> None:
    """503 + JSON inválido + 503 + válido: 2 intentos de validación y 2 pausas."""
    proveedor = ProveedorConFallos([ERROR_503, "no es json", ERROR_503, valida()])
    resultado = flujo(proveedor)
    assert resultado.intentos == 2
    assert len(resultado.errores_intentos) == 1
    assert pausas == [3.0, 8.0]
    assert len(proveedor.prompts_recibidos) == 4


def test_las_pausas_se_comparten_en_toda_la_invocacion(pausas: list[float]) -> None:
    """Agotadas las 2 repeticiones, un tercer 503 en otro intento falla sin esperar más."""
    rubrica = te._rubrica()
    proveedor = ProveedorConFallos(
        [ERROR_503, "no es json", ERROR_503, "no es json", ERROR_503, te._respuesta(rubrica)]
    )
    with pytest.raises(ErrorEvaluacion, match="Falló la llamada") as info:
        _evaluar(proveedor)
    assert pausas == [3.0, 8.0]
    assert len(info.value.errores) == 2


def test_validacion_sigue_limitada_a_max_retries(pausas: list[float]) -> None:
    """Con max_retries=0, un 503 se repite igual, pero un JSON inválido falla al primer intento."""
    proveedor = ProveedorConFallos([ERROR_503, "no es json"], max_retries=0)
    with pytest.raises(ErrorEvaluacion, match="tras 1 intento"):
        _evaluar(proveedor)
    assert pausas == [3.0]


class _SdkCodigoError(Exception):
    """Imita un error de SDK con código HTTP en `code` (Gemini) o `status_code` (OpenAI)."""

    def __init__(self, code: int | None = None, status_code: int | None = None) -> None:
        """Guarda el código en el atributo que usa cada SDK."""
        super().__init__("error del SDK")
        self.code = code
        self.status_code = status_code


@pytest.mark.parametrize("codigo", [429, 500, 503, 504])
def test_codigos_transitorios(codigo: int) -> None:
    """429, 500, 503 y 504 son transitorios, vengan en `code` o en `status_code`."""
    assert es_error_transitorio(_SdkCodigoError(code=codigo))
    assert es_error_transitorio(_SdkCodigoError(status_code=codigo))


@pytest.mark.parametrize("codigo", [400, 401, 403, 404])
def test_codigos_no_transitorios(codigo: int) -> None:
    """400, 401, 403 y 404 no son transitorios."""
    assert not es_error_transitorio(_SdkCodigoError(code=codigo))
    assert not es_error_transitorio(_SdkCodigoError(status_code=codigo))


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("lento"),
        ConnectionError("sin red"),
        httpx.ConnectError("sin red"),
        httpx.ReadTimeout("lento"),
    ],
)
def test_timeouts_y_conexion_son_transitorios(error: Exception) -> None:
    """Los timeouts y errores de conexión (Python y httpx) son transitorios."""
    assert es_error_transitorio(error)


def test_error_generico_no_es_transitorio() -> None:
    """Un error cualquiera sin código no es transitorio."""
    assert not es_error_transitorio(ValueError("x"))
    assert ErrorRespuestaLLM("x").transitorio is False


def _lanzar(error: Exception):
    """Devuelve una función que lanza el error indicado."""

    def funcion(**_: Any) -> Any:
        raise error

    return funcion


@pytest.mark.usefixtures("openai_falso")
@pytest.mark.parametrize(("codigo", "esperado"), [(503, True), (401, False)])
def test_openai_marca_transitorio(codigo: int, esperado: bool) -> None:
    """OpenAICompatProvider marca el ErrorRespuestaLLM según el código del SDK."""
    proveedor = _openai()
    proveedor._client.chat.completions.create = _lanzar(_SdkCodigoError(status_code=codigo))
    with pytest.raises(ErrorRespuestaLLM) as info:
        proveedor.generar_texto("p", _Esquema)
    assert info.value.transitorio is esperado


@pytest.mark.usefixtures("gemini_falso")
@pytest.mark.parametrize(("codigo", "esperado"), [(503, True), (429, True), (400, False)])
def test_gemini_marca_transitorio(codigo: int, esperado: bool) -> None:
    """GeminiProvider marca el ErrorRespuestaLLM según el código del SDK."""
    proveedor = _gemini()
    proveedor._client.models.generate_content = _lanzar(_SdkCodigoError(code=codigo))
    with pytest.raises(ErrorRespuestaLLM) as info:
        proveedor.generar_texto("p", _Esquema)
    assert info.value.transitorio is esperado


@pytest.mark.usefixtures("gemini_falso")
def test_respuesta_vacia_no_es_transitoria() -> None:
    """Una respuesta vacía del modelo no se repite como transitoria."""
    proveedor = _gemini()
    proveedor._client.models.generate_content = lambda **_: types.SimpleNamespace(text="")
    with pytest.raises(ErrorRespuestaLLM, match="vacía") as info:
        proveedor.generar_texto("p", _Esquema)
    assert info.value.transitorio is False


@pytest.fixture
def entorno_gemini(monkeypatch: pytest.MonkeyPatch, gemini_falso: None) -> pytest.MonkeyPatch:  # noqa: F811
    """Entorno mínimo para obtener_proveedor() con Gemini falso (sin red ni .env)."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
    return monkeypatch


def test_llm_max_retries_ausente_usa_2(entorno_gemini: pytest.MonkeyPatch) -> None:
    """Sin LLM_MAX_RETRIES el proveedor queda con 2 reintentos."""
    assert obtener_proveedor().max_retries == 2


@pytest.mark.parametrize(("texto", "esperado"), [("0", 0), ("1", 1), (" 2 ", 2), ("5", 2)])
def test_llm_max_retries_valido(
    entorno_gemini: pytest.MonkeyPatch, texto: str, esperado: int
) -> None:
    """LLM_MAX_RETRIES válido se pasa al proveedor (más de 2 se recorta a 2)."""
    entorno_gemini.setenv("LLM_MAX_RETRIES", texto)
    assert obtener_proveedor().max_retries == esperado


@pytest.mark.parametrize("texto", ["dos", "1.5", "-1"])
def test_llm_max_retries_invalido(entorno_gemini: pytest.MonkeyPatch, texto: str) -> None:
    """LLM_MAX_RETRIES no entero o negativo lanza ErrorConfiguracionLLM."""
    entorno_gemini.setenv("LLM_MAX_RETRIES", texto)
    with pytest.raises(ErrorConfiguracionLLM, match="LLM_MAX_RETRIES"):
        obtener_proveedor()


@pytest.mark.usefixtures("openai_falso")
def test_llm_max_retries_llega_a_openai_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    """obtener_proveedor() también pasa LLM_MAX_RETRIES a OpenAICompatProvider."""
    monkeypatch.setenv("LLM_PROVIDER", "openai_compat")
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "llama3")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    assert obtener_proveedor().max_retries == 1


def _peticion() -> httpx.Request:
    """Petición HTTP ficticia para construir errores reales de los SDK (no se envía)."""
    return httpx.Request("POST", "http://falso/v1")


def test_errores_reales_de_openai() -> None:
    """Clases reales del SDK de OpenAI: timeout y conexión son transitorios."""
    openai = pytest.importorskip("openai")
    assert es_error_transitorio(openai.APITimeoutError(request=_peticion()))
    assert es_error_transitorio(openai.APIConnectionError(request=_peticion()))


@pytest.mark.parametrize(("codigo", "esperado"), [(503, True), (429, True), (400, False)])
def test_errores_reales_de_gemini(codigo: int, esperado: bool) -> None:
    """Clases reales de google-genai: se clasifican por su atributo `code`."""
    errores = pytest.importorskip("google.genai.errors")
    clase = errores.ServerError if codigo >= 500 else errores.ClientError
    error = clase(codigo, {"error": {"code": codigo, "message": "x", "status": "X"}})
    assert es_error_transitorio(error) is esperado


def test_openai_desactiva_los_reintentos_del_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """El cliente OpenAI se crea con max_retries=0 para no apilar reintentos con comun.py."""
    recibido: dict[str, Any] = {}

    class _Capturador:
        """Imita openai.OpenAI guardando los argumentos del constructor."""

        def __init__(self, **kwargs: Any) -> None:
            """Guarda los argumentos recibidos."""
            recibido.update(kwargs)

    modulo = types.ModuleType("openai")
    modulo.OpenAI = _Capturador  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", modulo)
    _openai()
    assert recibido["max_retries"] == 0


def test_llm_max_retries_llega_a_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    """La rama fake de obtener_proveedor() también respeta LLM_MAX_RETRIES."""
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_MAX_RETRIES", "0")
    assert obtener_proveedor().max_retries == 0
