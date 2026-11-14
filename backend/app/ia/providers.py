"""Proveedores de LLM intercambiables con salida JSON validada por Pydantic."""

import base64
import json
import os
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

TEMPERATURA_MAXIMA = 0.2
MAX_REINTENTOS = 2
TIMEOUT_SEGUNDOS = 120.0
OLLAMA_BASE_URL = "http://localhost:11434/v1"


class ErrorRespuestaLLM(Exception):
    """El LLM falló o devolvió una respuesta que no cumple el esquema."""


class ErrorConfiguracionLLM(Exception):
    """La configuración del proveedor de IA es inválida o incompleta."""


def _detectar_mime(datos: bytes) -> str:
    """Detecta de forma simple si una imagen es PNG o JPEG."""
    if datos.startswith(b"\x89PNG"):
        return "image/png"
    return "image/jpeg"


def _limitar_temperatura(temperatura: float) -> float:
    """Acota la temperatura al rango [0, 0.2]."""
    return max(0.0, min(float(temperatura), TEMPERATURA_MAXIMA))


def _validar_max_retries(max_retries: int) -> int:
    """Valida los reintentos: negativo es error y más de MAX_REINTENTOS se recorta."""
    if max_retries < 0:
        raise ErrorConfiguracionLLM("max_retries no puede ser negativo.")
    return min(int(max_retries), MAX_REINTENTOS)


class LLMProvider(ABC):
    """Interfaz común: genera JSON validado contra un esquema Pydantic."""

    nombre: str = "base"
    max_retries: int = MAX_REINTENTOS

    def __init__(self, modelo: str, temperatura: float = 0.1) -> None:
        """Guarda modelo y temperatura (limitada a 0.2)."""
        self.modelo = modelo
        self.temperatura = _limitar_temperatura(temperatura)
        self.ultima_respuesta_cruda: str | None = None

    @abstractmethod
    def _llamar(self, prompt: str, schema: type[BaseModel], imagenes: list[bytes] | None) -> str:
        """Hace la llamada al modelo y devuelve el texto crudo."""

    def generar_texto(
        self, prompt: str, schema: type[BaseModel], imagenes: list[bytes] | None = None
    ) -> str:
        """Hace una sola llamada al modelo y devuelve el texto crudo, sin validar."""
        crudo = self._llamar(prompt, schema, imagenes)
        self.ultima_respuesta_cruda = crudo
        return crudo

    def generar_json(
        self, prompt: str, schema: type[T], imagenes: list[bytes] | None = None
    ) -> T:
        """Llama al modelo, valida con el esquema y reintenta hasta 2 veces si falla."""
        prompt_actual = prompt
        ultimo_error = ""
        for _ in range(self.max_retries + 1):
            crudo = self._llamar(prompt_actual, schema, imagenes)
            self.ultima_respuesta_cruda = crudo
            try:
                return schema.model_validate_json(crudo)
            except (ValidationError, ValueError) as error:
                ultimo_error = str(error)
                prompt_actual = (
                    f"{prompt}\n\n---\nTu respuesta anterior fue:\n{crudo}\n\n"
                    f"No cumple el esquema requerido. Error de validación:\n{ultimo_error}\n\n"
                    "Corrige la respuesta y devuelve SOLO el JSON válido, sin texto adicional."
                )
        raise ErrorRespuestaLLM(
            f"El modelo no devolvió un JSON válido tras {self.max_retries + 1} intentos. "
            f"Último error: {ultimo_error}"
        )


class GeminiProvider(LLMProvider):
    """Proveedor Google Gemini mediante la librería google-genai."""

    nombre = "gemini"

    def __init__(
        self,
        api_key: str,
        modelo: str = "gemini-3.5-flash-lite",
        temperatura: float = 0.1,
        timeout: float = TIMEOUT_SEGUNDOS,
        max_retries: int = MAX_REINTENTOS,
    ) -> None:
        """Crea el cliente de Gemini con timeout y reintentos (0 a 2)."""
        super().__init__(modelo, temperatura)
        self.max_retries = _validar_max_retries(max_retries)
        if not api_key:
            raise ErrorConfiguracionLLM("Falta GEMINI_API_KEY para usar el proveedor Gemini.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise ErrorConfiguracionLLM(
                "No está instalada la librería google-genai (pip install google-genai)."
            ) from error
        self._types = types
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout * 1000))
        )

    def _llamar(self, prompt: str, schema: type[BaseModel], imagenes: list[bytes] | None) -> str:
        """Envía el prompt (y las imágenes) a Gemini pidiendo JSON."""
        types = self._types
        contenidos: list = [prompt]
        for imagen in imagenes or []:
            contenidos.append(types.Part.from_bytes(data=imagen, mime_type=_detectar_mime(imagen)))
        config = types.GenerateContentConfig(
            temperature=self.temperatura,
            response_mime_type="application/json",
            response_schema=schema,
        )
        try:
            respuesta = self._client.models.generate_content(
                model=self.modelo, contents=contenidos, config=config
            )
        except Exception as error:  # se envuelve cualquier error del SDK
            raise ErrorRespuestaLLM(f"Error al llamar a Gemini ({self.modelo}): {error}") from error
        texto = respuesta.text
        if not texto:
            raise ErrorRespuestaLLM(f"Gemini ({self.modelo}) devolvió una respuesta vacía.")
        return texto


class OpenAICompatProvider(LLMProvider):
    """Proveedor compatible con la API de OpenAI (Ollama, Groq, OpenRouter...)."""

    nombre = "openai_compat"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        modelo: str,
        temperatura: float = 0.1,
        timeout: float = TIMEOUT_SEGUNDOS,
        max_retries: int = MAX_REINTENTOS,
    ) -> None:
        """Crea el cliente OpenAI apuntando a la base_url indicada, con reintentos (0 a 2)."""
        super().__init__(modelo, temperatura)
        self.max_retries = _validar_max_retries(max_retries)
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ErrorConfiguracionLLM(
                "No está instalada la librería openai (pip install openai)."
            ) from error
        self.base_url = base_url
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    def _llamar(self, prompt: str, schema: type[BaseModel], imagenes: list[bytes] | None) -> str:
        """Envía el prompt con el JSON Schema y pide respuesta en JSON."""
        esquema = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        texto = (
            f"{prompt}\n\nResponde ÚNICAMENTE con un objeto JSON que cumpla este JSON Schema:\n"
            f"{esquema}"
        )
        contenido: list[dict] = [{"type": "text", "text": texto}]
        for imagen in imagenes or []:
            b64 = base64.b64encode(imagen).decode("ascii")
            contenido.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{_detectar_mime(imagen)};base64,{b64}"},
                }
            )
        mensaje = contenido if imagenes else texto
        try:
            respuesta = self._client.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "user", "content": mensaje}],
                temperature=self.temperatura,
                response_format={"type": "json_object"},
            )
        except Exception as error:  # se envuelve cualquier error del SDK
            raise ErrorRespuestaLLM(
                f"Error al llamar al proveedor OpenAI-compatible ({self.base_url}, "
                f"{self.modelo}): {error}"
            ) from error
        salida = respuesta.choices[0].message.content if respuesta.choices else None
        if not salida:
            raise ErrorRespuestaLLM(f"El modelo {self.modelo} devolvió una respuesta vacía.")
        return salida


class FakeProvider(LLMProvider):
    """Proveedor de pruebas que devuelve respuestas fijas en orden."""

    nombre = "fake"

    def __init__(
        self,
        respuestas: list[str | dict | BaseModel],
        modelo: str = "fake-model",
        temperatura: float = 0.0,
    ) -> None:
        """Guarda las respuestas predefinidas."""
        super().__init__(modelo, temperatura)
        self.respuestas = list(respuestas)
        self.prompts_recibidos: list[str] = []
        self.imagenes_recibidas: list[list[bytes] | None] = []

    def _llamar(self, prompt: str, schema: type[BaseModel], imagenes: list[bytes] | None) -> str:
        """Devuelve la siguiente respuesta predefinida como texto."""
        self.prompts_recibidos.append(prompt)
        self.imagenes_recibidas.append(imagenes)
        if not self.respuestas:
            raise ErrorRespuestaLLM("FakeProvider se quedó sin respuestas predefinidas.")
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, BaseModel):
            return respuesta.model_dump_json()
        if isinstance(respuesta, dict):
            return json.dumps(respuesta, ensure_ascii=False)
        return respuesta


def obtener_proveedor() -> LLMProvider:
    """Construye el proveedor según las variables de entorno LLM_*."""
    nombre = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    modelo = os.environ.get("LLM_MODEL", "").strip()
    texto_temp = os.environ.get("LLM_TEMPERATURE", "0.1").strip() or "0.1"
    try:
        temperatura = _limitar_temperatura(float(texto_temp))
    except ValueError as error:
        raise ErrorConfiguracionLLM(
            f"LLM_TEMPERATURE debe ser un número (valor recibido: '{texto_temp}')."
        ) from error

    if nombre == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ErrorConfiguracionLLM("Falta GEMINI_API_KEY para usar el proveedor Gemini.")
        return GeminiProvider(
            api_key=api_key, modelo=modelo or "gemini-3.5-flash-lite", temperatura=temperatura
        )
    if nombre == "openai_compat":
        base_url = os.environ.get("OPENAI_COMPAT_BASE_URL", "").strip() or OLLAMA_BASE_URL
        api_key = os.environ.get("OPENAI_COMPAT_API_KEY", "").strip()
        if not api_key:
            if "localhost" in base_url or "127.0.0.1" in base_url:
                api_key = "ollama"
            else:
                raise ErrorConfiguracionLLM(
                    "Falta OPENAI_COMPAT_API_KEY para el proveedor OpenAI-compatible."
                )
        if not modelo:
            raise ErrorConfiguracionLLM("Falta LLM_MODEL para el proveedor OpenAI-compatible.")
        return OpenAICompatProvider(
            base_url=base_url, api_key=api_key, modelo=modelo, temperatura=temperatura
        )
    if nombre == "fake":
        return FakeProvider(respuestas=[], modelo=modelo or "fake-model", temperatura=temperatura)
    raise ErrorConfiguracionLLM(
        f"Proveedor de IA desconocido: '{nombre}'. Usa gemini, openai_compat o fake."
    )
