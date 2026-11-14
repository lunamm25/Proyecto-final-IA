"""Mapeo de criterios de la rúbrica a temáticas del curso con el LLM (RF-09 CA2)."""

import json
import re

from pydantic import BaseModel

from app.ia.comun import (
    BLOQUES_REINTENTO,
    ErrorIA,
    compilar_delimitadores,
    generar_con_reintentos,
    neutralizar_delimitadores,
    normalizar_nombre,
    resumir_lista,
    validar_esquema,
)
from app.ia.providers import LLMProvider
from app.ia.rubricas import cargar_prompt
from app.ia.schemas import MapeoCriterio, MapeoTematicasSchema, RubricaSchema

# Topes por campo para controlar el tamaño del prompt (los ids y las temáticas no se recortan).
LIMITE_CARACTERES_CAMPO = 300
LIMITE_CARACTERES_DESCRIPTOR = 600
LIMITE_CARACTERES_TEMATICA = 200
# Topes de tamaño que se validan antes de llamar al modelo (una rúbrica real tiene ~5-10
# criterios de 3-5 niveles y un curso unas decenas de temáticas). Exceder alguno es un error
# del docente o un abuso: se rechaza con ErrorMapeo en vez de enviar un prompt gigante.
MAX_CARACTERES_ID_CRITERIO = 50
MAX_CRITERIOS = 30
MAX_NIVELES_POR_CRITERIO = 10
MAX_TEMATICAS = 100
# Conceptos por criterio: el prompt pide entre 1 y 5. Si llegan más, se conservan los 5
# primeros (los extra no dañan el mapa y reintentar por eso gastaría tokens); si no llega
# ninguno, la respuesta es incoherente y se reintenta.
MAX_CONCEPTOS = 5
# Elementos que se muestran de cada listado en los mensajes de error (el resto: "y N más").
MAX_ELEMENTOS_EN_MENSAJE = 10

VERSION_PROMPT_MAPEO, _PLANTILLA_MAPEO = cargar_prompt("mapear_tematicas")
_MARCADORES = re.compile(r"\{(criterios|tematicas)\}")
DELIMITADORES_MAPEO = compilar_delimitadores(("criterios", "tematicas", *BLOQUES_REINTENTO))


class ErrorMapeo(ErrorIA):
    """El mapeo de criterios a temáticas no se pudo completar."""


class ResultadoMapeo(BaseModel):
    """Mapeo validado (temáticas con el nombre exacto de la lista) más la trazabilidad."""

    mapeo: MapeoTematicasSchema
    proveedor: str
    modelo: str
    temperatura: float
    version_prompt: str
    respuesta_cruda: str
    respuestas_crudas: list[str]
    intentos: int
    errores_intentos: list[str]


def _neutralizar(texto: str, limite: int | None = None) -> str:
    """Neutraliza los delimitadores de un texto del docente y lo recorta si hace falta."""
    limpio = neutralizar_delimitadores(texto.strip(), DELIMITADORES_MAPEO)
    return limpio[:limite] if limite else limpio


def _clave(texto: str) -> str:
    """Clave de comparación: el texto tal como lo ve el modelo, normalizado."""
    return normalizar_nombre(_neutralizar(texto))


def _listar(elementos: list[str]) -> str:
    """Listado recortado para los mensajes de error."""
    return resumir_lista(elementos, MAX_ELEMENTOS_EN_MENSAJE)


def preparar_tematicas(tematicas: list[str]) -> dict[str, str]:
    """Limpia la lista de temáticas: {clave normalizada: nombre exacto}, sin vacías ni repetidas.

    Dos temáticas que solo difieren en mayúsculas, acentos o espacios ("Ética de la IA" y
    "etica de la ia") son la misma: se unifican conservando la primera. Si dos temáticas
    distintas solo se vuelven iguales al neutralizar los delimitadores, el modelo no podría
    distinguirlas: se lanza ErrorMapeo.
    """
    resultado: dict[str, str] = {}
    for tematica in tematicas:
        nombre = tematica.strip()
        if not nombre:
            continue
        if len(nombre) > LIMITE_CARACTERES_TEMATICA:
            raise ErrorMapeo(
                f"La temática '{nombre[:60]}...' supera {LIMITE_CARACTERES_TEMATICA} caracteres."
            )
        previa = resultado.setdefault(_clave(nombre), nombre)
        if normalizar_nombre(previa) != normalizar_nombre(nombre):
            raise ErrorMapeo(
                f"Las temáticas '{previa[:60]}' y '{nombre[:60]}' quedan iguales al quitar los "
                "delimitadores del prompt (<<<, >>>, INICIO_*, FIN_*); renombra una de ellas."
            )
        if len(resultado) > MAX_TEMATICAS:
            raise ErrorMapeo(f"La lista tiene más de {MAX_TEMATICAS} temáticas; redúcela.")
    return resultado


def validar_rubrica_mapeo(rubrica: RubricaSchema) -> None:
    """Rechaza rúbricas vacías, demasiado grandes o con ids que el modelo no distinguiría."""
    if not rubrica.criterios:
        raise ErrorMapeo("La rúbrica no tiene criterios; no se puede mapear a temáticas.")
    if len(rubrica.criterios) > MAX_CRITERIOS:
        raise ErrorMapeo(
            f"La rúbrica tiene {len(rubrica.criterios)} criterios; el máximo es {MAX_CRITERIOS}."
        )
    vistos: dict[str, str] = {}
    for posicion, criterio in enumerate(rubrica.criterios, start=1):
        if len(criterio.id) > MAX_CARACTERES_ID_CRITERIO:
            raise ErrorMapeo(
                f"El id del criterio {posicion} supera {MAX_CARACTERES_ID_CRITERIO} caracteres."
            )
        if len(criterio.niveles) > MAX_NIVELES_POR_CRITERIO:
            raise ErrorMapeo(
                f"El criterio {criterio.id} tiene {len(criterio.niveles)} niveles; el máximo "
                f"es {MAX_NIVELES_POR_CRITERIO}."
            )
        previo = vistos.setdefault(_neutralizar(criterio.id), criterio.id)
        if previo != criterio.id:
            raise ErrorMapeo(
                f"Los ids de criterio '{previo}' y '{criterio.id}' quedan iguales al quitar los "
                "delimitadores del prompt (<<<, >>>, INICIO_*, FIN_*); renombra uno de ellos."
            )


def construir_prompt_mapeo(rubrica: RubricaSchema, tematicas: list[str]) -> str:
    """Rellena la plantilla con los criterios y temáticas neutralizados (sin ponderaciones)."""
    criterios = [
        {
            "id": _neutralizar(c.id),
            "competencia": _neutralizar(c.competencia, LIMITE_CARACTERES_CAMPO),
            "nombre": _neutralizar(c.nombre, LIMITE_CARACTERES_CAMPO),
            "niveles": [
                {
                    "nombre": _neutralizar(n.nombre, LIMITE_CARACTERES_CAMPO),
                    "descriptor": _neutralizar(n.descriptor, LIMITE_CARACTERES_DESCRIPTOR),
                }
                for n in c.niveles
            ],
        }
        for c in rubrica.criterios
    ]
    nombres = [_neutralizar(t) for t in preparar_tematicas(tematicas).values()]
    valores = {
        "criterios": json.dumps(criterios, ensure_ascii=False, indent=2),
        "tematicas": json.dumps(nombres, ensure_ascii=False, indent=2),
    }
    return _MARCADORES.sub(lambda m: valores[m.group(1)], _PLANTILLA_MAPEO)


def _limpiar_conceptos(conceptos: list[str]) -> list[str]:
    """Quita conceptos vacíos o repetidos y deja como máximo MAX_CONCEPTOS."""
    vistos: dict[str, str] = {}
    for concepto in conceptos:
        texto = " ".join(concepto.split())
        if texto:
            vistos.setdefault(normalizar_nombre(texto), texto)
    return list(vistos.values())[:MAX_CONCEPTOS]


def _errores_criterios(recibidos: list[str], rubrica: RubricaSchema) -> list[str]:
    """Errores de criterios faltantes, inexistentes o repetidos (con listados recortados)."""
    ids = [c.id for c in rubrica.criterios]
    faltantes = [cid for cid in ids if cid not in recibidos]
    extras = sorted({cid for cid in recibidos if cid not in ids})
    repetidos = sorted({cid for cid in recibidos if recibidos.count(cid) > 1})
    errores = []
    if faltantes:
        errores.append(f"Faltan criterios de la rúbrica: {_listar(faltantes)}.")
    if extras:
        errores.append(f"Hay criterios que no existen en la rúbrica: {_listar(extras)}.")
    if repetidos:
        errores.append(f"Hay criterios repetidos: {_listar(repetidos)}.")
    return errores


def validar_mapeo(
    mapeo: MapeoTematicasSchema, rubrica: RubricaSchema, tematicas: dict[str, str]
) -> tuple[MapeoTematicasSchema, list[str]]:
    """Comprueba criterios completos, sin extras ni repetidos, temáticas de la lista y conceptos.

    Las temáticas se comparan sin mayúsculas, acentos ni espacios extra y se guardan con el
    nombre exacto de la lista. Los criterios se devuelven en el orden de la rúbrica.
    """
    ids = {_neutralizar(c.id): c.id for c in rubrica.criterios}
    ids.update({c.id: c.id for c in rubrica.criterios})
    recibidos = [ids.get(m.criterio_id, m.criterio_id) for m in mapeo.mapeos]
    errores = _errores_criterios(recibidos, rubrica)
    desconocidas: list[str] = []
    sin_tematicas: list[str] = []
    sin_conceptos: list[str] = []
    por_id: dict[str, MapeoCriterio] = {}
    for item, criterio_id in zip(mapeo.mapeos, recibidos, strict=True):
        if criterio_id not in ids.values() or criterio_id in por_id:
            continue
        exactas: list[str] = []
        for tematica in item.tematicas:
            nombre = tematicas.get(_clave(tematica))
            if nombre is None:
                desconocidas.append(f"'{tematica}' ({criterio_id})")
            elif nombre not in exactas:
                exactas.append(nombre)
        conceptos = _limpiar_conceptos(item.conceptos)
        if not item.tematicas:
            sin_tematicas.append(criterio_id)
        if not conceptos:
            sin_conceptos.append(criterio_id)
        por_id[criterio_id] = MapeoCriterio(
            criterio_id=criterio_id, tematicas=exactas, conceptos=conceptos
        )
    if desconocidas:
        errores.append(f"Hay temáticas que no están en la lista del curso: {_listar(desconocidas)}.")
    if sin_tematicas:
        errores.append(f"Criterios sin ninguna temática asociada: {_listar(sin_tematicas)}.")
    if sin_conceptos:
        errores.append(
            f"Criterios sin conceptos (deben tener entre 1 y {MAX_CONCEPTOS}): "
            f"{_listar(sin_conceptos)}."
        )
    ordenados = [por_id[c.id] for c in rubrica.criterios if c.id in por_id]
    return MapeoTematicasSchema(mapeos=ordenados), errores


def _interpretar(
    crudo: str, rubrica: RubricaSchema, tematicas: dict[str, str]
) -> tuple[MapeoTematicasSchema | None, str]:
    """Valida el JSON crudo contra el esquema y la coherencia; devuelve (mapeo, error)."""
    mapeo, error = validar_esquema(crudo, MapeoTematicasSchema)
    if mapeo is None:
        return None, error
    mapeo, errores = validar_mapeo(mapeo, rubrica, tematicas)
    if errores:
        validas = _listar(list(tematicas.values()))
        return None, (
            "No es coherente con la rúbrica y las temáticas: "
            + " ".join(errores)
            + f" Temáticas válidas: {validas} (la lista completa está en el bloque TEMATICAS)."
        )
    return mapeo, ""


def mapear_criterios_a_tematicas(
    rubrica: RubricaSchema, tematicas: list[str], proveedor: LLMProvider
) -> ResultadoMapeo:
    """Asocia cada criterio con temáticas de la lista; valida y reintenta hasta 2 veces."""
    validar_rubrica_mapeo(rubrica)
    validas = preparar_tematicas(tematicas)
    if not validas:
        raise ErrorMapeo("La lista de temáticas del curso está vacía; no se puede mapear.")
    resultado = generar_con_reintentos(
        proveedor,
        construir_prompt_mapeo(rubrica, tematicas),
        MapeoTematicasSchema,
        lambda crudo: _interpretar(crudo, rubrica, validas),
        ErrorMapeo,
        "un mapeo de temáticas válido",
        DELIMITADORES_MAPEO,
    )
    return ResultadoMapeo(
        mapeo=resultado.valor,
        proveedor=proveedor.nombre,
        modelo=proveedor.modelo,
        temperatura=proveedor.temperatura,
        version_prompt=VERSION_PROMPT_MAPEO,
        respuesta_cruda=resultado.respuesta_cruda,
        respuestas_crudas=resultado.respuestas_crudas,
        intentos=resultado.intentos,
        errores_intentos=resultado.errores,
    )
