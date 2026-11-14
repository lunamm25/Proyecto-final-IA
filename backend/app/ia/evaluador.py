"""Evaluación cualitativa de un laboratorio con el LLM (RF-05). El LLM nunca calcula la nota."""

import json
import re
from typing import Any

from pydantic import BaseModel

from app.ia.citas import ResultadoCita, normalizar_fuente, verificar_citas_normalizadas
from app.ia.comun import (
    DELIMITADOR_ELIMINADO,
    LIMITE_CARACTERES_ERROR,
    LIMITE_CARACTERES_RESPUESTA_ANTERIOR,
    MARCADOR_OMITIDO,
    PROPORCION_INICIO,
    SIN_INFORMACION,
    ErrorIA,
    describir_error_validacion,
    generar_con_reintentos,
    neutralizar_delimitadores,
    prompt_con_error,
    recortar_texto,
    validar_esquema,
)
from app.ia.providers import LLMProvider
from app.ia.rubricas import cargar_prompt
from app.ia.schemas import EvaluacionLLMSchema, RubricaSchema

# Límites de contexto en caracteres (~4 caracteres por token). 30 000 caracteres de informe
# son unas 7 500 palabras (≈ 15 páginas): cubre un informe normal y deja margen en modelos
# pequeños. Si se excede, se conserva el inicio (70 %) y el final (30 %, conclusiones).
LIMITE_CARACTERES_INFORME = 30_000
LIMITE_CARACTERES_CODIGO = 12_000
LIMITE_CARACTERES_VERIFICACION = 6_000
# Las claves del dict de verificación se conservan (dan sentido a cada número) pero se acortan.
LIMITE_CARACTERES_CLAVE = 80

# Reexportados desde app.ia.comun para no romper los imports existentes.
__all__ = [
    "DELIMITADOR_ELIMINADO",
    "LIMITE_CARACTERES_ERROR",
    "LIMITE_CARACTERES_RESPUESTA_ANTERIOR",
    "MARCADOR_OMITIDO",
    "PROPORCION_INICIO",
    "SIN_INFORMACION",
    "ErrorEvaluacion",
    "ResultadoEvaluacion",
    "construir_prompt_evaluacion",
    "describir_error_validacion",
    "evaluar_laboratorio",
    "neutralizar_delimitadores",
    "prompt_con_error",
    "recortar_texto",
    "validar_coherencia",
]

VERSION_PROMPT_EVALUAR, _PLANTILLA_EVALUAR = cargar_prompt("evaluar_laboratorio")
_MARCADORES = re.compile(
    r"\{(descripcion|objetivos|rubrica|texto_informe|resumen_codigo|resultados_verificacion"
    r"|verificacion_texto)\}"
)


class ErrorEvaluacion(ErrorIA):
    """La evaluación no se pudo completar; la entrega debe quedar en estado `error`."""


class ResultadoEvaluacion(BaseModel):
    """Evaluación validada más los datos de trazabilidad (sin nota)."""

    evaluacion: EvaluacionLLMSchema
    citas: list[ResultadoCita]
    proveedor: str
    modelo: str
    temperatura: float
    version_prompt: str
    respuesta_cruda: str
    respuestas_crudas: list[str]
    intentos: int
    errores_intentos: list[str]
    informe_recortado: bool


def _solo_numeros(valor: Any) -> Any:
    """Conserva recursivamente solo números y booleanos (con sus claves); descarta el texto."""
    if isinstance(valor, (bool, int, float)):
        return valor
    if isinstance(valor, dict):
        filtrado = {}
        for clave, interno in valor.items():
            limpio = _solo_numeros(interno)
            if limpio is not None:
                filtrado[neutralizar_delimitadores(str(clave))[:LIMITE_CARACTERES_CLAVE]] = limpio
        return filtrado or None
    if isinstance(valor, (list, tuple)):
        filtrada = [v for v in (_solo_numeros(x) for x in valor) if v is not None]
        return filtrada or None
    return None


def separar_verificacion(resultados: Any) -> tuple[str, str]:
    """Devuelve (conteos objetivos en JSON, texto libre no confiable ya neutralizado)."""
    if isinstance(resultados, str):
        texto = neutralizar_delimitadores(resultados)
        return "", recortar_texto(texto, LIMITE_CARACTERES_VERIFICACION)
    numeros = _solo_numeros(resultados)
    if numeros is None:
        return "", ""
    conteos = json.dumps(numeros, ensure_ascii=False, indent=2)
    return recortar_texto(conteos, LIMITE_CARACTERES_VERIFICACION), ""


def _a_texto(valor: Any) -> str:
    """Convierte str, lista o dict a texto legible para el prompt."""
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, list) and all(isinstance(v, str) for v in valor):
        return "\n".join(f"- {v.strip()}" for v in valor)
    return json.dumps(valor, ensure_ascii=False, indent=2, default=str)


def construir_prompt_evaluacion(
    rubrica: RubricaSchema,
    descripcion: str,
    objetivos: str | list[str],
    texto_informe: str,
    resumen_codigo: str | None,
    resultados_verificacion: Any,
) -> str:
    """Rellena la plantilla con el contexto neutralizado y recortado (en una sola pasada)."""
    conteos, texto_verificacion = separar_verificacion(resultados_verificacion)
    informe = neutralizar_delimitadores(texto_informe)
    codigo = neutralizar_delimitadores(_a_texto(resumen_codigo))
    valores = {
        "descripcion": _a_texto(descripcion) or SIN_INFORMACION,
        "objetivos": _a_texto(objetivos) or SIN_INFORMACION,
        "rubrica": rubrica.model_dump_json(indent=2),
        "texto_informe": recortar_texto(informe, LIMITE_CARACTERES_INFORME) or SIN_INFORMACION,
        "resumen_codigo": recortar_texto(codigo, LIMITE_CARACTERES_CODIGO) or SIN_INFORMACION,
        "resultados_verificacion": conteos or SIN_INFORMACION,
        "verificacion_texto": texto_verificacion or SIN_INFORMACION,
    }
    return _MARCADORES.sub(lambda m: valores[m.group(1)], _PLANTILLA_EVALUAR)


def validar_coherencia(
    evaluacion: EvaluacionLLMSchema, rubrica: RubricaSchema
) -> tuple[EvaluacionLLMSchema, list[str]]:
    """Comprueba criterios completos, sin extras ni repetidos, y niveles válidos."""
    errores: list[str] = []
    por_id = {c.id: c for c in rubrica.criterios}
    recibidos = [c.criterio_id for c in evaluacion.criterios]
    faltantes = [cid for cid in por_id if cid not in recibidos]
    extras = sorted({cid for cid in recibidos if cid not in por_id})
    repetidos = sorted({cid for cid in recibidos if recibidos.count(cid) > 1})
    if faltantes:
        errores.append(f"Faltan criterios de la rúbrica: {', '.join(faltantes)}.")
    if extras:
        errores.append(f"Hay criterios que no existen en la rúbrica: {', '.join(extras)}.")
    if repetidos:
        errores.append(f"Hay criterios repetidos: {', '.join(repetidos)}.")
    corregidos = []
    for item in evaluacion.criterios:
        criterio = por_id.get(item.criterio_id)
        if criterio is None:
            continue
        nombres = {n.nombre.strip().casefold(): n.nombre for n in criterio.niveles}
        nombre = nombres.get(item.nivel_elegido.strip().casefold())
        if nombre is None:
            validos = ", ".join(n.nombre for n in criterio.niveles)
            errores.append(
                f"El nivel '{item.nivel_elegido}' no existe en el criterio {criterio.id} "
                f"(niveles válidos: {validos})."
            )
        corregidos.append(item.model_copy(update={"nivel_elegido": nombre or item.nivel_elegido}))
    return evaluacion.model_copy(update={"criterios": corregidos}), errores


def _interpretar(crudo: str, rubrica: RubricaSchema) -> tuple[EvaluacionLLMSchema | None, str]:
    """Valida el JSON crudo contra el esquema y la rúbrica; devuelve (evaluación, error)."""
    evaluacion, error = validar_esquema(crudo, EvaluacionLLMSchema)
    if evaluacion is None:
        return None, error
    evaluacion, errores = validar_coherencia(evaluacion, rubrica)
    if errores:
        return None, "No es coherente con la rúbrica: " + " ".join(errores)
    return evaluacion, ""


def _material_citable(
    texto_informe: str, resumen_codigo: str | None, resultados_verificacion: Any
) -> str:
    """Une el material tal como lo ve el modelo (neutralizado) para verificar las citas."""
    conteos, texto_verificacion = separar_verificacion(resultados_verificacion)
    partes = [
        neutralizar_delimitadores(texto_informe),
        neutralizar_delimitadores(_a_texto(resumen_codigo)),
        conteos,
        texto_verificacion,
    ]
    return "\n".join(p for p in partes if p)


def _verificar_evidencias(
    evaluacion: EvaluacionLLMSchema, material: str
) -> list[ResultadoCita]:
    """Verifica todas las evidencias normalizando el material una sola vez."""
    fuente = normalizar_fuente(material)
    resultados: list[ResultadoCita] = []
    for item in evaluacion.criterios:
        resultados.extend(verificar_citas_normalizadas(item.evidencias, fuente, item.criterio_id))
    return resultados


def evaluar_laboratorio(
    rubrica: RubricaSchema,
    descripcion: str,
    objetivos: str | list[str],
    texto_informe: str,
    resumen_codigo: str | None,
    resultados_verificacion: Any,
    proveedor: LLMProvider,
) -> ResultadoEvaluacion:
    """Evalúa una entrega con el LLM, valida, reintenta hasta 2 veces y verifica las citas."""
    if not rubrica.criterios:
        raise ErrorEvaluacion("La rúbrica no tiene criterios; no se puede evaluar.")
    base = construir_prompt_evaluacion(
        rubrica, descripcion, objetivos, texto_informe, resumen_codigo, resultados_verificacion
    )
    resultado = generar_con_reintentos(
        proveedor,
        base,
        EvaluacionLLMSchema,
        lambda crudo: _interpretar(crudo, rubrica),
        ErrorEvaluacion,
        "una evaluación válida",
    )
    evaluacion = resultado.valor
    material = _material_citable(texto_informe, resumen_codigo, resultados_verificacion)
    return ResultadoEvaluacion(
        evaluacion=evaluacion,
        citas=_verificar_evidencias(evaluacion, material),
        proveedor=proveedor.nombre,
        modelo=proveedor.modelo,
        temperatura=proveedor.temperatura,
        version_prompt=VERSION_PROMPT_EVALUAR,
        respuesta_cruda=resultado.respuesta_cruda,
        respuestas_crudas=resultado.respuestas_crudas,
        intentos=resultado.intentos,
        errores_intentos=resultado.errores,
        informe_recortado=len(texto_informe.strip()) > LIMITE_CARACTERES_INFORME,
    )
