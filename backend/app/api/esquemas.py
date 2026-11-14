"""Esquemas Pydantic de las respuestas de la API (no son los del LLM)."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class PerfilRespuesta(BaseModel):
    """Perfil público del usuario autenticado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    rol: Literal["estudiante", "docente", "admin"]
    foto_url: str | None


class UsuarioRespuesta(BaseModel):
    """Usuario en la gestión de roles (solo admin)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    correo: str | None
    rol: Literal["estudiante", "docente", "admin"]


class CambioRolEntrada(BaseModel):
    """Nuevo rol de un usuario y motivo opcional (queda en auditoría)."""

    rol: str = Field(
        description="Uno de: estudiante, docente o admin.",
        json_schema_extra={"enum": ["estudiante", "docente", "admin"]},
        examples=["docente"],
    )
    motivo: str | None = Field(default=None, max_length=500, examples=["Monitor del curso"])


class LaboratorioEntrada(BaseModel):
    """Datos para crear o editar un laboratorio."""

    cohorte_id: int
    codigo: str
    titulo: str
    descripcion: str | None = None
    objetivos: str | None = None


class LaboratorioRespuesta(BaseModel):
    """Laboratorio de una cohorte."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cohorte_id: int
    codigo: str
    titulo: str
    descripcion: str | None
    objetivos: str | None


class LaboratorioEnCohorte(LaboratorioRespuesta):
    """Laboratorio con el número de su versión de rúbrica vigente (None si no tiene)."""

    version_rubrica_vigente: int | None = None


class CohorteRespuesta(BaseModel):
    """Cohorte con sus laboratorios ordenados por código."""

    id: int
    nombre: str
    numero: int
    laboratorios: list[LaboratorioEnCohorte]


class ValidacionRubricaRespuesta(BaseModel):
    """Resultado del validador: válida si no hay inconsistencias."""

    valida: bool
    inconsistencias: list[str]


class RubricaVersionRespuesta(BaseModel):
    """Versión inmutable de una rúbrica."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    estado: Literal["borrador", "aprobada"]
    contenido: dict[str, Any]
    creada_por: uuid.UUID | None
    creada_en: datetime


class ErrorRespuesta(BaseModel):
    """Forma estándar de los errores: mensaje en español."""

    detail: str


class ErrorRubricaRespuesta(ErrorRespuesta):
    """Error 422 al guardar una rúbrica con inconsistencias."""

    inconsistencias: list[str]


EstadoEvaluacion = Literal[
    "procesando", "borrador", "en_revision", "aprobada", "publicada", "error"
]


class EvaluacionLanzadaRespuesta(BaseModel):
    """Respuesta 202 al lanzar una evaluación: se procesa en segundo plano."""

    evaluacion_id: int
    estado: EstadoEvaluacion = Field(examples=["procesando"])


class CitaRespuesta(BaseModel):
    """Evidencia citada por la IA y su verificación contra el material (similitud 0–100)."""

    fragmento: str
    fuente: str
    ubicacion: str | None = None
    verificada: bool
    similitud: float


class RetroalimentacionCriterioIA(BaseModel):
    """Textos de un criterio tal como los propuso la IA."""

    justificacion: str | None = None
    fortalezas: list[str] = []
    debilidades: list[str] = []
    recomendacion: str | None = None


class CriterioEvaluacionRespuesta(BaseModel):
    """Resultado de un criterio. `nivel_ia` y `ajuste_docente` solo los ve el docente."""

    criterio_id: str
    nivel_ia: str | None = None
    nivel_final: str | None
    puntaje_normalizado: float | None
    justificacion: str | None
    citas: list[CitaRespuesta]
    fortalezas: list[str] = []
    debilidades: list[str] = []
    recomendacion: str | None = None
    ajuste_docente: str | None = None
    original_ia: RetroalimentacionCriterioIA | None = Field(
        default=None, description="Textos originales de la IA (solo docente/admin)."
    )


class RetroalimentacionRespuesta(BaseModel):
    """Retroalimentación general de la evaluación."""

    aprendizajes_identificados: list[str] = []
    como_aplico_conocimientos: str | None = None
    aspectos_a_fortalecer: list[str] = []
    retroalimentacion_general: str | None = None


class EvaluacionRespuesta(BaseModel):
    """Detalle de una evaluación (nunca incluye respuestas crudas del LLM).

    Para el estudiante, proveedor, modelo, temperatura y prompt_version van en null.
    """

    id: int
    entrega_id: int
    estado: EstadoEvaluacion
    nota: float | None
    rubrica_version_id: int | None
    rubrica_version: int | None
    proveedor: str | None = None
    modelo: str | None = None
    temperatura: float | None = None
    prompt_version: str | None = None
    error: str | None
    criterios: list[CriterioEvaluacionRespuesta]
    retroalimentacion: RetroalimentacionRespuesta | None
    retroalimentacion_ia: RetroalimentacionRespuesta | None = Field(
        default=None, description="Retroalimentación original de la IA (solo docente/admin)."
    )
    creada_en: datetime
    aprobada_en: datetime | None
    publicada_en: datetime | None


# ---------- Revisión docente (RF-07) ----------

TextoCorto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
TextoLargo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
ListaTextos = Annotated[list[TextoCorto], Field(max_length=30)]


class AjusteCriterioEntrada(BaseModel):
    """Nuevo nivel y motivo obligatorio. La nota NO se envía: la calcula el backend."""

    nivel_final: str = Field(min_length=1, max_length=200, examples=["Bueno"])
    motivo: TextoCorto = Field(examples=["El código no maneja errores de entrada."])


class RetroalimentacionCriterioEntrada(BaseModel):
    """Textos editados de un criterio. Omitido = sin cambios; null = volver al texto de la IA."""

    criterio_id: str = Field(min_length=1, examples=["C1"])
    justificacion: TextoLargo | None = None
    fortalezas: ListaTextos | None = None
    debilidades: ListaTextos | None = None
    recomendacion: TextoLargo | None = None


class RetroalimentacionEntrada(BaseModel):
    """Edición de la retroalimentación. Omitido = sin cambios; null = volver al texto de la IA."""

    retroalimentacion_general: TextoLargo | None = Field(default=None, examples=["Buen trabajo."])
    como_aplico_conocimientos: TextoLargo | None = None
    aprendizajes_identificados: ListaTextos | None = None
    aspectos_a_fortalecer: ListaTextos | None = None
    criterios: list[RetroalimentacionCriterioEntrada] = Field(default=[], max_length=50)
    motivo: str | None = Field(default=None, max_length=1000, examples=["Tono más cercano"])


class EstudianteResumen(BaseModel):
    """Estudiante en el listado de evaluaciones."""

    id: uuid.UUID
    nombre: str | None


class LaboratorioResumen(BaseModel):
    """Laboratorio en el listado de evaluaciones."""

    id: int
    codigo: str
    titulo: str


class EvaluacionResumen(BaseModel):
    """Fila del listado docente (sin resultados ni respuestas crudas)."""

    id: int
    entrega_id: int
    estudiante: EstudianteResumen
    laboratorio: LaboratorioResumen
    estado: EstadoEvaluacion
    nota: float | None
    creada_en: datetime
    aprobada_en: datetime | None
    publicada_en: datetime | None


class ListadoEvaluacionesRespuesta(BaseModel):
    """Página del listado: `total` cuenta todas las que cumplen los filtros."""

    items: list[EvaluacionResumen]
    total: int
    limit: int
    offset: int


class UsuarioTraza(BaseModel):
    """Quién hizo la acción."""

    id: uuid.UUID
    nombre: str | None


class EventoTrazaRespuesta(BaseModel):
    """Evento de auditoría (fechas en UTC). `usuario` es null si lo hizo el sistema."""

    id: int
    fecha: datetime
    usuario: UsuarioTraza | None
    accion: str
    antes: Any | None
    despues: Any | None
    motivo: str | None


class TrazaRespuesta(BaseModel):
    """Trazabilidad completa de una evaluación (solo docente/admin)."""

    evaluacion_id: int
    entrega_id: int
    estado: EstadoEvaluacion
    nota: float | None
    proveedor: str | None
    modelo: str | None
    temperatura: float | None
    prompt_version: str | None
    rubrica_version_id: int | None
    rubrica_version: int | None
    eventos: list[EventoTrazaRespuesta]


# ---------- Estudiantes: listado, informe (RF-08) y mapa (RF-09) ----------

NivelDominio = Literal["bajo", "medio", "alto"]


class EstudianteListado(BaseModel):
    """Estudiante en el listado docente con sus laboratorios evaluados (publicados)."""

    id: uuid.UUID
    nombre: str | None
    correo: str | None
    laboratorios_evaluados: int = Field(
        description="Laboratorios distintos con al menos una evaluación publicada."
    )


class ListadoEstudiantesRespuesta(BaseModel):
    """Página del listado de estudiantes."""

    items: list[EstudianteListado]
    total: int
    limit: int
    offset: int


class LaboratorioInformeRespuesta(BaseModel):
    """Nota de un laboratorio (evaluación publicada más reciente)."""

    laboratorio_id: int
    codigo: str
    titulo: str
    cohorte: str
    cohorte_numero: int
    nota: float | None
    evaluacion_id: int
    publicada_en: datetime | None


class PromedioCohorteRespuesta(BaseModel):
    """Promedio de las notas de una cohorte (null si no tiene laboratorios evaluados)."""

    cohorte: str
    cohorte_numero: int
    promedio: float | None
    laboratorios_evaluados: int


class CompetenciaInformeRespuesta(BaseModel):
    """Dominio 0–5 de una competencia: promedio de normalizado × 5 de sus criterios."""

    competencia: str
    promedio: float | None
    nivel_dominio: NivelDominio | None
    criterios_evaluados: int


class TematicaInformeRespuesta(BaseModel):
    """Dominio 0–5 de una temática (incluye los criterios de sus subtemas)."""

    tematica_id: int
    tematica: str
    promedio: float | None
    nivel_dominio: NivelDominio | None
    criterios_evaluados: int


class EvolucionRespuesta(BaseModel):
    """Promedio de la última cohorte − promedio de la primera (null si falta alguno)."""

    cohorte_inicial: str
    cohorte_final: str
    promedio_inicial: float | None
    promedio_final: float | None
    diferencia: float | None


class AccionPlanRespuesta(BaseModel):
    """Acción del plan de fortalecimiento (redactada por la IA)."""

    accion: str
    recurso: str
    prioridad: str
    competencia: str


class NarrativaRespuesta(BaseModel):
    """Textos de la IA. `estado`: generada, sin_datos, no_disponible o error (con `mensaje`)."""

    estado: Literal["generada", "sin_datos", "no_disponible", "error"]
    mensaje: str | None = None
    competencias_desarrolladas: list[str] = []
    brechas: list[str] = []
    plan_fortalecimiento: list[AccionPlanRespuesta] = []
    conclusion: str | None = None
    generada_en: datetime | None = None


class InformeRespuesta(BaseModel):
    """Informe integrado: los números los calcula el backend; la narrativa va aparte."""

    estudiante: EstudianteResumen
    laboratorios_evaluados: int
    laboratorios: list[LaboratorioInformeRespuesta]
    promedios_cohorte: list[PromedioCohorteRespuesta]
    promedio_general: float | None
    competencias: list[CompetenciaInformeRespuesta]
    tematicas: list[TematicaInformeRespuesta]
    evolucion: EvolucionRespuesta | None
    narrativa: NarrativaRespuesta
    avisos: list[str]


class EvidenciaMapaRespuesta(BaseModel):
    """Cita verificada que respalda un nodo."""

    fragmento: str
    fuente: str
    ubicacion: str | None
    laboratorio: str
    criterio_id: str


class NodoMapaRespuesta(BaseModel):
    """Nodo del mapa: temática, subtema, concepto, competencia o laboratorio."""

    id: str = Field(examples=["tematica:3", "concepto:3:perceptron", "lab:C1-01"])
    tipo: Literal["tematica", "subtema", "concepto", "competencia", "laboratorio"]
    etiqueta: str
    dominio: float | None = Field(description="0–5; en laboratorios, su nota.")
    nivel_dominio: NivelDominio | None
    evidencias: list[EvidenciaMapaRespuesta]
    aspectos_por_profundizar: list[str]
    laboratorios: list[str]


class AristaMapaRespuesta(BaseModel):
    """Relación padre → hijo del mapa."""

    origen: str
    destino: str


class MapaRespuesta(BaseModel):
    """Grafo {nodos, aristas} del mapa de conocimiento y avisos para el usuario."""

    nodos: list[NodoMapaRespuesta]
    aristas: list[AristaMapaRespuesta]
    avisos: list[str]


class ConfigIAEntrada(BaseModel):
    """Nueva configuración de IA: solo proveedor, modelo y temperatura (sin claves ni URL)."""

    model_config = ConfigDict(extra="forbid")

    proveedor: str = Field(
        description="Uno de: gemini u openai_compat.",
        json_schema_extra={"enum": ["gemini", "openai_compat"]},
        examples=["gemini"],
    )
    modelo: str = Field(min_length=1, max_length=100, examples=["gemini-3.5-flash-lite"])
    temperatura: float = Field(ge=0, le=0.2, strict=True, allow_inf_nan=False, examples=[0.1])


class ActorRespuesta(BaseModel):
    """Usuario que hizo un cambio (id y nombre)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None


class ClavesIARespuesta(BaseModel):
    """Solo indica si cada secreto está configurado en el servidor; nunca su valor."""

    gemini_api_key_configurada: bool
    openai_compat_api_key_configurada: bool
    openai_compat_base_url_configurada: bool


class ProveedorPermitido(BaseModel):
    """Proveedor elegible con sus modelos permitidos (para el selector del panel)."""

    proveedor: str
    etiqueta: str
    modelos: list[str]


class ConfigIARespuesta(BaseModel):
    """Configuración de IA vigente, origen, claves configuradas y opciones permitidas."""

    model_config = ConfigDict(from_attributes=True)

    proveedor: str
    modelo: str
    temperatura: float
    origen: Literal["base_de_datos", "entorno"]
    modelo_permitido: bool
    actualizado_por: ActorRespuesta | None
    actualizado_en: datetime | None
    temperatura_maxima: float
    claves: ClavesIARespuesta
    proveedores_permitidos: list[ProveedorPermitido]
    versiones_prompt: dict[str, str | None]
