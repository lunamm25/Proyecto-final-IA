// Tipos del contrato de API (docs/REQUISITOS.md §7, §10 y §11).
// La nota (0,0–5,0) siempre la calcula el backend: en el frontend solo se muestra.

export type Rol = "estudiante" | "docente" | "admin";

export type JsonValor = string | number | boolean | null | JsonValor[] | { [clave: string]: JsonValor };

/** Respuesta de error del backend. FastAPI devuelve una lista en los errores de validación (422). */
export interface DetalleValidacion {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ErrorRespuesta {
  detail: string | DetalleValidacion[];
}

// ---------- Usuarios (RF-01) ----------

/** GET /api/yo (PerfilRespuesta del backend). El backend no envía el correo. */
export interface Perfil {
  id: string;
  nombre: string | null;
  rol: Rol;
  foto_url: string | null;
  /** Solo en modo mock (el rol simulado sale del correo); la API real no lo envía. */
  email?: string;
}

/** GET /api/usuarios (UsuarioRespuesta del backend). */
export interface Usuario {
  id: string;
  nombre: string | null;
  correo: string | null;
  rol: Rol;
}

/** PATCH /api/usuarios/{id}/rol (CambioRolEntrada del backend). */
export interface CambioRol {
  rol: Rol;
  motivo?: string;
}

// ---------- Cohortes y laboratorios (RF-02) ----------

/**
 * Ids numéricos del backend (cohortes, laboratorios, entregas, evaluaciones, versiones de rúbrica).
 * Los de usuarios son UUID (string). Los ids que llegan por la URL se convierten con `idDesdeUrl`.
 */
export type IdNumerico = number;

/** Convierte un id que llega por la URL ("3") en número; null si no es un entero positivo válido. */
export function idDesdeUrl(valor: string): IdNumerico | null {
  if (!/^\d{1,15}$/.test(valor)) return null;
  const id = Number(valor);
  return id > 0 ? id : null;
}

/** LaboratorioRespuesta del backend. */
export interface Laboratorio {
  id: IdNumerico;
  cohorte_id: IdNumerico;
  codigo: string;
  titulo: string;
  descripcion: string | null;
  objetivos: string | null;
}

/** LaboratorioEnCohorte: dentro de GET /api/cohortes trae la versión vigente de su rúbrica. */
export interface LaboratorioEnCohorte extends Laboratorio {
  /** null = sin rúbrica aprobada. */
  version_rubrica_vigente: number | null;
}

/** Cuerpo de POST/PUT /api/laboratorios (LaboratorioEntrada del backend). */
export type LaboratorioEntrada = Omit<Laboratorio, "id">;

/** GET /api/cohortes (CohorteRespuesta) */
export interface Cohorte {
  id: IdNumerico;
  nombre: string;
  numero: number;
  laboratorios: LaboratorioEnCohorte[];
}

// ---------- Rúbricas (RF-03, RubricaSchema §7) ----------

export interface NivelDesempeno {
  nombre: string;
  puntaje: number;
  descriptor: string;
}

export interface CriterioRubrica {
  id: string;
  competencia: string;
  nombre: string;
  /** Porcentaje; la suma de todos los criterios debe ser 100. */
  ponderacion: number;
  niveles: NivelDesempeno[];
}

export interface Rubrica {
  titulo: string;
  criterios: CriterioRubrica[];
}

export type TipoInconsistencia =
  | "ponderaciones_no_suman_100"
  | "criterio_sin_niveles"
  | "niveles_insuficientes"
  | "nivel_sin_puntaje"
  | "nivel_sin_descriptor"
  | "nivel_duplicado"
  | "puntajes_no_ordenados"
  | "criterio_duplicado"
  | "competencia_vacia";

export interface Inconsistencia {
  tipo: TipoInconsistencia;
  mensaje: string;
  criterio_id: string | null;
}

/**
 * POST /api/rubricas/validar (ValidacionRubricaRespuesta): el backend devuelve las inconsistencias
 * como textos. Los objetos `Inconsistencia` son solo de la validación en vivo del cliente.
 */
export interface ResultadoValidacion {
  valida: boolean;
  inconsistencias: string[];
}

/** POST /api/laboratorios/{id}/rubrica/extraer (aún no existe en el backend; misma convención de textos). */
export interface ResultadoExtraccion {
  rubrica: Rubrica;
  inconsistencias: string[];
}

export type EstadoVersionRubrica = "borrador" | "aprobada";

/** GET /api/laboratorios/{id}/rubrica y POST .../rubrica/versiones (RubricaVersionRespuesta). */
export interface RubricaVersion {
  id: IdNumerico;
  version: number;
  estado: EstadoVersionRubrica;
  contenido: Rubrica;
  /** UUID de quien la creó. */
  creada_por: string | null;
  creada_en: string;
}

// ---------- Entregas (RF-04) ----------

/** EstadoEvaluacion del backend: "procesando" mientras corre el pipeline en segundo plano. */
export type EstadoEvaluacion = "procesando" | "borrador" | "en_revision" | "aprobada" | "publicada" | "error";

export interface ResumenEvaluacion {
  id: IdNumerico;
  estado: EstadoEvaluacion;
  /** Calculada por el backend; null mientras no exista o no sea visible para el usuario. */
  nota: number | null;
}

/** GET /api/entregas (aún no existe en el backend; ids con la misma convención). */
export interface Entrega {
  id: IdNumerico;
  /** UUID del estudiante. */
  estudiante_id: string;
  laboratorio_id: IdNumerico;
  rubrica_version_id: IdNumerico;
  pdf_path: string;
  codigo_zip_path: string | null;
  github_url: string | null;
  extras: string[];
  creada_en: string;
  /** null = sin evaluar. */
  evaluacion: ResumenEvaluacion | null;
}

/** Datos del formulario para POST /api/entregas (se envían como multipart/form-data). */
export interface NuevaEntrega {
  laboratorio_id: IdNumerico;
  pdf: File;
  zip?: File;
  github_url?: string;
  extras?: File[];
}

/** POST /api/entregas/{id}/evaluar → 202 (EvaluacionLanzadaRespuesta; estado "procesando"). */
export interface RespuestaEvaluar {
  evaluacion_id: IdNumerico;
  estado: EstadoEvaluacion;
}

// ---------- Evaluaciones (RF-05, RF-06, RF-07) ----------

export type FuenteEvidencia = "informe" | "codigo" | "verificacion" | "imagen";

export interface Evidencia {
  fragmento: string;
  fuente: FuenteEvidencia;
  ubicacion: string | null;
  /** false = la cita no se encontró en el material (posible alucinación). */
  verificada: boolean;
}

export interface EvaluacionCriterio {
  criterio_id: string;
  nombre: string;
  competencia: string;
  ponderacion: number;
  nivel_ia: string;
  nivel_final: string;
  evidencias: Evidencia[];
  justificacion: string;
  fortalezas: string[];
  debilidades: string[];
  recomendacion: string;
  /** Motivo del último ajuste del docente; null si no hubo ajuste. */
  ajuste_docente: string | null;
}

export interface ResultadoSintaxis {
  archivo: string;
  valido: boolean;
  error: string | null;
}

export interface ResultadoRuff {
  errores: number;
  advertencias: number;
  mensajes: string[];
}

export interface ResultadoComplejidad {
  promedio: number;
  maxima: number;
  rango: string;
}

export interface ResultadoTests {
  ejecutados: boolean;
  aprobados: number;
  fallidos: number;
  detalle: string | null;
}

export interface MetricasCodigo {
  archivos: number;
  lineas: number;
  tiene_readme: boolean;
  tiene_requirements: boolean;
  tiene_tests: boolean;
  lenguajes: string[];
}

export interface VerificacionCodigo {
  sintaxis: ResultadoSintaxis[];
  ruff: ResultadoRuff;
  complejidad: ResultadoComplejidad;
  tests: ResultadoTests;
  metricas: MetricasCodigo;
  sandbox: string;
  limitaciones: string[];
}

/** GET /api/evaluaciones/{id} */
export interface Evaluacion {
  id: IdNumerico;
  entrega_id: IdNumerico;
  /** UUID. Pendiente en el backend (hoy EvaluacionRespuesta no lo trae). */
  estudiante_id: string;
  /** Pendiente en el backend (hoy EvaluacionRespuesta no lo trae). */
  laboratorio_id: IdNumerico;
  estado: EstadoEvaluacion;
  /** Calculada por el backend (0,0–5,0). El frontend nunca la calcula. */
  nota: number | null;
  proveedor: string;
  modelo: string;
  prompt_version: string;
  temperatura: number;
  rubrica_version: number;
  criterios: EvaluacionCriterio[];
  aprendizajes_identificados: string[];
  como_aplico_conocimientos: string;
  aspectos_a_fortalecer: string[];
  retroalimentacion_general: string;
  verificacion: VerificacionCodigo | null;
  error: string | null;
  creada_en: string;
  aprobada_en: string | null;
  publicada_en: string | null;
}

/** PATCH /api/evaluaciones/{id}/criterios/{criterio_id} */
export interface AjusteCriterio {
  nivel_final: string;
  motivo: string;
}

export interface RegistroAuditoria {
  id: string;
  usuario_id: string;
  usuario_nombre: string;
  accion: string;
  antes: JsonValor;
  despues: JsonValor;
  motivo: string | null;
  creado_en: string;
}

/** GET /api/evaluaciones/{id}/traza */
export interface Traza {
  evaluacion_id: IdNumerico;
  proveedor: string;
  modelo: string;
  prompt_version: string;
  temperatura: number;
  rubrica_version: number;
  respuesta_cruda: JsonValor;
  verificacion: VerificacionCodigo | null;
  auditoria: RegistroAuditoria[];
}

// ---------- Informe (RF-08, InformeNarrativoSchema §7) ----------

export type NivelDominio = "sin_evidencia" | "bajo" | "medio" | "alto";

export type Prioridad = "alta" | "media" | "baja";

export interface NotaLaboratorio {
  laboratorio_id: IdNumerico;
  codigo: string;
  titulo: string;
  cohorte: number;
  evaluacion_id: IdNumerico;
  nota: number;
}

export interface PromedioCohorte {
  cohorte: number;
  promedio: number | null;
}

export interface DominioCompetencia {
  competencia: string;
  /** 0 a 1, calculado por el backend. */
  dominio: number;
  nivel: NivelDominio;
}

export interface Evolucion {
  cohorte_1: number | null;
  cohorte_2: number | null;
  diferencia: number | null;
}

export interface AccionPlan {
  accion: string;
  recurso: string;
  prioridad: Prioridad;
  competencia: string;
}

export interface InformeNarrativo {
  competencias_desarrolladas: string[];
  brechas: string[];
  plan_fortalecimiento: AccionPlan[];
  conclusion: string;
}

/** GET /api/estudiantes/{id}/informe */
export interface Informe {
  estudiante_id: string;
  estudiante_nombre: string;
  notas_laboratorio: NotaLaboratorio[];
  promedios_cohorte: PromedioCohorte[];
  promedio_general: number | null;
  dominio_competencias: DominioCompetencia[];
  evolucion: Evolucion;
  narrativa: InformeNarrativo | null;
  generado_en: string;
}

// ---------- Mapa mental (RF-09) ----------

export type TipoNodo = "tematica" | "concepto" | "laboratorio";

export interface NodoMapa {
  id: string;
  etiqueta: string;
  tipo: TipoNodo;
  padre_id: string | null;
  nivel: NivelDominio;
  /** 0 a 1, calculado por el backend; null si no hay evidencia. */
  dominio: number | null;
  laboratorios: string[];
  evidencias: string[];
  por_profundizar: string[];
}

export interface AristaMapa {
  id: string;
  origen: string;
  destino: string;
}

/** GET /api/estudiantes/{id}/mapa */
export interface Mapa {
  nodos: NodoMapa[];
  aristas: AristaMapa[];
}

// ---------- Configuración de IA (RF-10) ----------

export type ProveedorIA = "gemini" | "openai_compatible";

/** GET /api/config-ia */
export interface ConfigIA {
  proveedor: ProveedorIA;
  modelo: string;
  temperatura: number;
  actualizado_por: string | null;
  actualizado_en: string | null;
}

/** Cuerpo de PUT /api/config-ia */
export interface ConfigIAEntrada {
  proveedor: ProveedorIA;
  modelo: string;
  temperatura: number;
}

/** POST /api/config-ia/probar */
export interface ResultadoPruebaIA {
  ok: boolean;
  mensaje: string;
}
