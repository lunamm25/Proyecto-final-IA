"""Narrativa del informe integrado del estudiante con el LLM (RF-08 CA3).

Las cifras (notas, promedios, evolución) las calcula el backend y llegan en `DatosDesempeno`.
El modelo solo redacta: se rechaza cualquier cifra del texto que no esté en esos datos.

Limitaciones conocidas del control de cifras: no detecta números escritos con palabras
("cuatro coma siete") ni una cifra real de los datos atribuida al campo equivocado (p. ej.
el promedio de una temática presentado como nota de un laboratorio).
"""

import json
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from app.ia.comun import (
    BLOQUES_REINTENTO,
    ErrorIA,
    compilar_delimitadores,
    describir_error_validacion,
    generar_con_reintentos,
    neutralizar_delimitadores,
    normalizar_nombre,
    validar_esquema,
)
from app.ia.providers import LLMProvider
from app.ia.rubricas import cargar_prompt
from app.ia.schemas import InformeNarrativoSchema

LIMITE_CARACTERES_NOMBRE = 200
MAX_ELEMENTOS = 100

VERSION_PROMPT_INFORME, _PLANTILLA_INFORME = cargar_prompt("informe_narrativo")
_MARCADORES = re.compile(r"\{(datos)\}")
DELIMITADORES_INFORME = compilar_delimitadores(("datos", *BLOQUES_REINTENTO))

# Cifras del texto generado: números con coma o punto decimal y signo opcional, completos
# aunque lleven letras detrás ("4.9pts", "3,9x"). No se toman los pegados por delante a letras,
# guiones o puntos (LAB03, SHA-256, GPT-4), que son identificadores.
_CIFRA_TEXTO = re.compile(r"(?<![\w.,\-−])[-−]?\d+(?:[.,]\d+)?(?![.,]?\d)")
# En los textos de los datos (p. ej. "LAB03", "Cohorte 2026-1") se aceptan todos los números.
_CIFRA_DATOS = re.compile(r"\d+(?:[.,]\d+)?")
# Años (enteros 1900–2100) que el texto puede mencionar sin estar en los datos.
ANIO_MINIMO, ANIO_MAXIMO = 1900, 2100
# Enteros siempre aceptados: los límites de la escala de notas ("3,5 sobre 5", "de 0 a 5").
ENTEROS_ESCALA = frozenset({Decimal(0), Decimal(5)})
# Expresiones que se quitan del texto antes de buscar cifras porque no son resultados:
# - referencias a partes de un material: "capítulo 4", "sección 2.3", "tema 3", "página 12";
# - cantidades de tiempo o de trabajo: "30 minutos", "2 horas", "3 ejercicios", "10 páginas";
# - rangos de enteros: "3-4", "2-3 semanas";
# - versiones de software (ver _VERSION).
_REFERENCIA = re.compile(
    r"\b(?:cap[ií]tulos?|cap\.|secci[oó]n(?:es)?|apartados?|unidad(?:es)?|m[oó]dulos?|temas?"
    r"|figuras?|tablas?|p[aá]ginas?|pasos?|ejemplos?)\s+\d+(?:\.\d+)*",
    re.IGNORECASE,
)
_UNIDADES = (
    r"minutos?|min|horas?|d[ií]as?|semanas?|mes(?:es)?|sesi[oó]n(?:es)?|ejercicios?"
    r"|p[aá]ginas?|lecturas?|v[ií]deos?|problemas?|preguntas?"
)
_CANTIDAD = re.compile(
    rf"(?<![\w.,\-−])\d+(?:[.,]\d+)?\s*(?:{_UNIDADES})\b", re.IGNORECASE
)
_RANGO = re.compile(r"(?<![\w.,\-−])\d+\s*[-–]\s*\d+(?![.,]?\d)")
# Versiones de software: "Python 3.12", "Python 3,12", "versión 3.12.4", "v3.12", "3.12.x".
_SOFTWARE = r"python|pytest|pip|node(?:\.js)?|java|django|fastapi|numpy|pandas|ruff|ollama"
_VERSION = re.compile(
    rf"\b(?:(?:{_SOFTWARE}|versi[oó]n(?:es)?)\s+v?|v)\d+(?:[.,]\d+)*(?:\.x)?\b"
    r"|(?<![\w.,\-−])\d+(?:\.\d+)+\.x\b",
    re.IGNORECASE,
)
# Datos personales que no deben llegar al modelo: correos y secuencias de 7 o más dígitos
# (documentos, teléfonos), también con puntos de miles ("1.020.304.050").
_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DOCUMENTO = re.compile(r"\d{7,}|\d{1,3}(?:\.\d{3}){2,}")


def _sin_datos_personales(texto: str) -> str:
    """Rechaza textos con un correo o un número largo (sin repetir el valor en el error)."""
    if _CORREO.search(texto) or _DOCUMENTO.search(texto):
        raise ValueError(
            "parece contener un correo o un número de documento o teléfono; no se admiten "
            "datos personales"
        )
    return texto


Nombre = Annotated[
    str,
    Field(min_length=1, max_length=LIMITE_CARACTERES_NOMBRE),
    AfterValidator(_sin_datos_personales),
]
Nota = Annotated[float, Field(ge=0.0, le=5.0)]


class _Datos(BaseModel):
    """Base de los datos de entrada: no admite campos desconocidos."""

    model_config = ConfigDict(extra="forbid")


class NotaLaboratorio(_Datos):
    """Nota (calculada por el backend) de un laboratorio publicado."""

    laboratorio: Nombre
    cohorte: Nombre
    nota: Nota | None = None


class PromedioCohorte(_Datos):
    """Promedio de las notas de una cohorte."""

    cohorte: Nombre
    promedio: Nota | None = None


class DesempenoTematica(_Datos):
    """Promedio y nivel de dominio en una temática del curso."""

    tematica: Nombre
    promedio: Nota | None = None
    nivel_dominio: Nombre | None = None


class DesempenoCompetencia(_Datos):
    """Promedio y nivel de dominio en una competencia de las rúbricas."""

    competencia: Nombre
    promedio: Nota | None = None
    nivel_dominio: Nombre | None = None


class EvolucionCohortes(_Datos):
    """Evolución entre dos cohortes (la diferencia la calcula el backend)."""

    cohorte_inicial: Nombre
    cohorte_final: Nombre
    promedio_inicial: Nota | None = None
    promedio_final: Nota | None = None
    diferencia: float | None = None


class DatosDesempeno(_Datos):
    """Cifras ya calculadas por el backend que el modelo usa para redactar (sin datos personales)."""

    laboratorios: list[NotaLaboratorio] = Field(default_factory=list, max_length=MAX_ELEMENTOS)
    promedios_cohorte: list[PromedioCohorte] = Field(default_factory=list, max_length=10)
    promedio_general: Nota | None = None
    tematicas: list[DesempenoTematica] = Field(default_factory=list, max_length=MAX_ELEMENTOS)
    competencias: list[DesempenoCompetencia] = Field(
        default_factory=list, max_length=MAX_ELEMENTOS
    )
    evolucion: list[EvolucionCohortes] = Field(default_factory=list, max_length=10)


class ErrorInforme(ErrorIA):
    """La narrativa del informe no se pudo generar."""


class ResultadoInforme(BaseModel):
    """Narrativa validada más la trazabilidad (sin nota ni cifras calculadas por la IA)."""

    informe: InformeNarrativoSchema
    proveedor: str
    modelo: str
    temperatura: float
    version_prompt: str
    respuesta_cruda: str
    respuestas_crudas: list[str]
    intentos: int
    errores_intentos: list[str]


def _neutralizar(texto: str) -> str:
    """Neutraliza los delimitadores del prompt en un texto de los datos."""
    return neutralizar_delimitadores(texto, DELIMITADORES_INFORME)


def _clave(texto: str) -> str:
    """Clave de comparación: el texto tal como lo ve el modelo, normalizado."""
    return normalizar_nombre(_neutralizar(texto))


def _neutralizar_valores(valor: Any) -> Any:
    """Neutraliza recursivamente todos los textos (claves y valores) de una estructura."""
    if isinstance(valor, str):
        return _neutralizar(valor)
    if isinstance(valor, dict):
        return {_neutralizar(str(k)): _neutralizar_valores(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_neutralizar_valores(v) for v in valor]
    return valor


def _validar_datos(datos_desempeno: BaseModel | dict) -> DatosDesempeno:
    """Valida un dict o modelo ajeno como DatosDesempeno; ErrorInforme sin mostrar valores."""
    if isinstance(datos_desempeno, BaseModel):
        datos_desempeno = datos_desempeno.model_dump(mode="json")
    try:
        return DatosDesempeno.model_validate(datos_desempeno)
    except ValidationError as error:
        raise ErrorInforme(
            "Los datos de desempeño no tienen el formato esperado: "
            + describir_error_validacion(error)
        ) from error


def preparar_datos(datos_desempeno: DatosDesempeno | BaseModel | dict) -> DatosDesempeno:
    """Convierte el dict o modelo recibido en DatosDesempeno, con un error claro si no encaja."""
    if isinstance(datos_desempeno, DatosDesempeno):
        datos = datos_desempeno
    else:
        datos = _validar_datos(datos_desempeno)
    if not (datos.laboratorios or datos.tematicas or datos.competencias):
        raise ErrorInforme(
            "No hay laboratorios, temáticas ni competencias en los datos; no se puede redactar "
            "el informe."
        )
    return datos


def construir_prompt_informe(datos: DatosDesempeno) -> str:
    """Rellena la plantilla con los datos en JSON, con todos los textos neutralizados."""
    limpio = _neutralizar_valores(datos.model_dump(mode="json"))
    valores = {"datos": json.dumps(limpio, ensure_ascii=False, indent=2)}
    return _MARCADORES.sub(lambda m: valores[m.group(1)], _PLANTILLA_INFORME)


def _a_decimal(texto: str) -> Decimal | None:
    """Convierte '4,25' o '-0.4' en su valor absoluto exacto (None si no es un número)."""
    try:
        return Decimal(texto.replace("−", "-").replace(",", ".")).copy_abs()
    except InvalidOperation:
        return None


def _decimales(cifra: str) -> int:
    """Número de decimales con que está escrita una cifra ('3,50' → 2, '4' → 0)."""
    partes = re.split(r"[.,]", cifra)
    return len(partes[1]) if len(partes) > 1 else 0


def cifras_permitidas(datos: DatosDesempeno) -> set[Decimal]:
    """Valores exactos que el texto puede citar: números de los datos, de sus textos y conteos.

    Los conteos son los tamaños de las listas no vacías: una lista vacía no autoriza el 0.
    """
    permitidas: set[Decimal] = set()

    def recorrer(valor: Any) -> None:
        """Agrega los números encontrados en la estructura."""
        if isinstance(valor, bool) or valor is None:
            return
        if isinstance(valor, (int, float)):
            cifras = [repr(float(valor))]
        elif isinstance(valor, str):
            cifras = _CIFRA_DATOS.findall(valor)
        elif isinstance(valor, dict):
            cifras = []
            for interno in valor.values():
                recorrer(interno)
        elif isinstance(valor, list):
            cifras = [str(len(valor))] if valor else []
            for interno in valor:
                recorrer(interno)
        else:
            return
        permitidas.update(r for r in map(_a_decimal, cifras) if r is not None)

    recorrer(datos.model_dump(mode="json"))
    return permitidas


def _es_anio(texto: str) -> bool:
    """Indica si la cifra es un año entero (1900–2100)."""
    return texto.isdigit() and ANIO_MINIMO <= int(texto) <= ANIO_MAXIMO


def _respaldada(cifra: str, permitidas: set[Decimal], revisar_enteros: bool) -> bool:
    """Indica si la cifra coincide con algún dato redondeado a los decimales con que se escribió.

    Así "3,5" está respaldada por 3,52, pero "3,49" no lo está por 3,5. Los enteros se aceptan
    si son años, límites de la escala (0 y 5) o si el campo no revisa enteros.
    """
    valor = _a_decimal(cifra)
    if valor is None:
        return True
    decimales = _decimales(cifra)
    if decimales == 0 and (
        not revisar_enteros or _es_anio(cifra.lstrip("-−")) or valor in ENTEROS_ESCALA
    ):
        return True
    paso = Decimal(1).scaleb(-decimales)
    return any(p.quantize(paso, rounding=ROUND_HALF_UP) == valor for p in permitidas)


def _cifras_texto(texto: str) -> list[str]:
    """Cifras de un texto tras quitar referencias, versiones, cantidades y rangos."""
    for patron in (_REFERENCIA, _VERSION, _RANGO, _CANTIDAD):
        texto = patron.sub(" ", texto)
    return _CIFRA_TEXTO.findall(texto)


def _textos_informe(informe: InformeNarrativoSchema) -> list[tuple[str, bool]]:
    """Textos redactados por el modelo con un indicador de si se revisan las cifras enteras.

    En `accion` y `recurso` del plan los enteros suelen ser cantidades ("leer 2 artículos") y
    no se revisan; las cifras decimales sí.
    """
    textos = [(t, True) for t in [*informe.competencias_desarrolladas, *informe.brechas]]
    textos.append((informe.conclusion, True))
    for accion in informe.plan_fortalecimiento:
        textos.extend([(accion.accion, False), (accion.recurso, False), (accion.competencia, True)])
    return textos


def cifras_no_respaldadas(informe: InformeNarrativoSchema, datos: DatosDesempeno) -> list[str]:
    """Devuelve las cifras del texto que no aparecen en los datos (sin repetir, en orden)."""
    permitidas = cifras_permitidas(datos)
    inventadas: list[str] = []
    for texto, revisar_enteros in _textos_informe(informe):
        for cifra in _cifras_texto(texto):
            if cifra not in inventadas and not _respaldada(cifra, permitidas, revisar_enteros):
                inventadas.append(cifra)
    return inventadas


def nombres_referenciables(datos: DatosDesempeno) -> dict[str, str]:
    """Temáticas, competencias y laboratorios de los datos: {clave normalizada: nombre exacto}."""
    nombres = [t.tematica for t in datos.tematicas]
    nombres += [c.competencia for c in datos.competencias]
    nombres += [lab.laboratorio for lab in datos.laboratorios]
    resultado: dict[str, str] = {}
    for nombre in nombres:
        resultado.setdefault(_clave(nombre), nombre)
    return resultado


def validar_informe(
    informe: InformeNarrativoSchema, datos: DatosDesempeno
) -> tuple[InformeNarrativoSchema, list[str]]:
    """Comprueba listas no vacías, el plan (referencias existentes) y que no haya cifras inventadas."""
    errores: list[str] = []
    referenciables = nombres_referenciables(datos)
    if not any(t.strip() for t in informe.competencias_desarrolladas):
        errores.append("'competencias_desarrolladas' debe tener al menos un texto no vacío.")
    if not any(t.strip() for t in informe.brechas):
        errores.append("'brechas' debe tener al menos un texto no vacío.")
    if not informe.plan_fortalecimiento:
        errores.append("El plan de fortalecimiento debe tener al menos una acción.")
    if not informe.conclusion.strip():
        errores.append("La conclusión no puede estar vacía.")
    plan = []
    for indice, accion in enumerate(informe.plan_fortalecimiento, start=1):
        nombre = referenciables.get(_clave(accion.competencia))
        if nombre is None:
            errores.append(
                f"La acción {indice} del plan referencia '{accion.competencia}', que no es una "
                "temática, competencia ni laboratorio de los datos."
            )
        plan.append(accion.model_copy(update={"competencia": nombre or accion.competencia}))
    inventadas = cifras_no_respaldadas(informe, datos)
    if inventadas:
        errores.append(
            "El texto menciona cifras que no están en los datos calculados por el sistema: "
            f"{', '.join(inventadas)}. Copia solo cifras de los datos o describe el desempeño "
            "sin cifras."
        )
    return informe.model_copy(update={"plan_fortalecimiento": plan}), errores


def _interpretar(
    crudo: str, datos: DatosDesempeno
) -> tuple[InformeNarrativoSchema | None, str]:
    """Valida el JSON crudo contra el esquema y los datos; devuelve (informe, error)."""
    informe, error = validar_esquema(crudo, InformeNarrativoSchema)
    if informe is None:
        return None, error
    informe, errores = validar_informe(informe, datos)
    if errores:
        validos = ", ".join(nombres_referenciables(datos).values())
        return None, (
            "No es coherente con los datos de desempeño: "
            + " ".join(errores)
            + f" Nombres válidos para 'competencia': {validos}."
        )
    return informe, ""


def generar_informe_narrativo(
    datos_desempeno: DatosDesempeno | BaseModel | dict, proveedor: LLMProvider
) -> ResultadoInforme:
    """Redacta la narrativa del informe a partir de cifras ya calculadas; valida y reintenta."""
    datos = preparar_datos(datos_desempeno)
    resultado = generar_con_reintentos(
        proveedor,
        construir_prompt_informe(datos),
        InformeNarrativoSchema,
        lambda crudo: _interpretar(crudo, datos),
        ErrorInforme,
        "una narrativa de informe válida",
        DELIMITADORES_INFORME,
    )
    return ResultadoInforme(
        informe=resultado.valor,
        proveedor=proveedor.nombre,
        modelo=proveedor.modelo,
        temperatura=proveedor.temperatura,
        version_prompt=VERSION_PROMPT_INFORME,
        respuesta_cruda=resultado.respuesta_cruda,
        respuestas_crudas=resultado.respuestas_crudas,
        intentos=resultado.intentos,
        errores_intentos=resultado.errores,
    )
