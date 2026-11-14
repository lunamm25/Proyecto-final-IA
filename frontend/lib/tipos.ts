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

/** CitaRespuesta: evidencia citada por la IA y su verificación contra el material (RF-05 CA3). */
export interface Cita {
  fragmento: string;
  /** Texto libre del backend ("informe", "codigo", "verificacion", "imagen"...). */
  fuente: string;
  ubicacion: string | null;
  /** false = la cita no se encontró en el material (posible alucinación). */
  verificada: boolean;
  /** Similitud con el material, de 0 a 100; la calcula el backend. */
  similitud: number;
}

/** RetroalimentacionCriterioIA: textos originales de la IA para un criterio (solo docente/admin). */
export interface RetroalimentacionCriterioIA {
  justificacion: string | null;
  fortalezas: string[];
  debilidades: string[];
  recomendacion: string | null;
}

/** CriterioEvaluacionRespuesta: textos finales (editados por el docente o de la IA). */
export interface EvaluacionCriterio {
  criterio_id: string;
  nivel_ia: string | null;
  nivel_final: string | null;
  puntaje_normalizado: number | null;
  justificacion: string | null;
  citas: Cita[];
  fortalezas: string[];
  debilidades: string[];
  recomendacion: string | null;
  /** Motivo del último ajuste del docente; null si no hubo ajuste. */
  ajuste_docente: string | null;
  original_ia: RetroalimentacionCriterioIA | null;
}

/** RetroalimentacionRespuesta: retroalimentación general de la evaluación. */
export interface Retroalimentacion {
  aprendizajes_identificados: string[];
  como_aplico_conocimientos: string | null;
  aspectos_a_fortalecer: string[];
  retroalimentacion_general: string | null;
}

/**
 * GET /api/evaluaciones/{id} (EvaluacionRespuesta). Para el estudiante, proveedor, modelo, temperatura y
 * prompt_version llegan en null. El backend aún no envía laboratorio ni estudiante (pedido a Rol 2): si los
 * agrega se usan; si no, la pantalla los toma de la URL (?lab=&est=).
 */
export interface Evaluacion {
  id: IdNumerico;
  entrega_id: IdNumerico;
  estado: EstadoEvaluacion;
  /** Calculada por el backend (0,0–5,0). El frontend nunca la calcula. */
  nota: number | null;
  rubrica_version_id: IdNumerico | null;
  rubrica_version: number | null;
  proveedor: string | null;
  modelo: string | null;
  temperatura: number | null;
  prompt_version: string | null;
  error: string | null;
  criterios: EvaluacionCriterio[];
  retroalimentacion: Retroalimentacion | null;
  /** Retroalimentación original de la IA (solo docente/admin). */
  retroalimentacion_ia: Retroalimentacion | null;
  creada_en: string;
  aprobada_en: string | null;
  publicada_en: string | null;
  laboratorio_id?: IdNumerico;
  estudiante_id?: string;
}

/** PATCH /api/evaluaciones/{id}/criterios/{criterio_id} (AjusteCriterioEntrada). */
export interface AjusteCriterio {
  nivel_final: string;
  motivo: string;
}

/** Textos de un criterio. Omitido = sin cambios; null = volver al texto de la IA. */
export interface RetroalimentacionCriterioEntrada {
  criterio_id: string;
  justificacion?: string | null;
  fortalezas?: string[] | null;
  debilidades?: string[] | null;
  recomendacion?: string | null;
}

/** PATCH /api/evaluaciones/{id}/retroalimentacion (RetroalimentacionEntrada). Omitido = sin cambios; null = texto de la IA. */
export interface RetroalimentacionEntrada {
  retroalimentacion_general?: string | null;
  como_aplico_conocimientos?: string | null;
  aprendizajes_identificados?: string[] | null;
  aspectos_a_fortalecer?: string[] | null;
  criterios?: RetroalimentacionCriterioEntrada[];
  motivo?: string;
}

/** GET /api/evaluaciones: fila del listado docente (EvaluacionResumen). */
export interface EvaluacionResumen {
  id: IdNumerico;
  entrega_id: IdNumerico;
  estudiante: { id: string; nombre: string | null };
  laboratorio: { id: IdNumerico; codigo: string; titulo: string };
  estado: EstadoEvaluacion;
  nota: number | null;
  creada_en: string;
  aprobada_en: string | null;
  publicada_en: string | null;
}

/** Filtros de GET /api/evaluaciones. */
export interface FiltrosEvaluaciones {
  estado?: EstadoEvaluacion;
  laboratorio_id?: IdNumerico;
  estudiante_id?: string;
  limit?: number;
  offset?: number;
}

/** Respuesta paginada (ListadoEvaluacionesRespuesta). */
export interface ListadoEvaluaciones {
  items: EvaluacionResumen[];
  total: number;
  limit: number;
  offset: number;
}

/** GET /api/estudiantes (docente): EstudianteListado. */
export interface EstudianteListado {
  id: string;
  nombre: string | null;
  correo: string | null;
  /** Laboratorios distintos con al menos una evaluación publicada (lo calcula el backend). */
  laboratorios_evaluados: number;
}

export interface ListadoEstudiantes {
  items: EstudianteListado[];
  total: number;
  limit: number;
  offset: number;
}

/** EventoTrazaRespuesta: `usuario` es null si la acción la hizo el sistema. Fechas en UTC. */
export interface EventoTraza {
  id: IdNumerico;
  fecha: string;
  usuario: { id: string; nombre: string | null } | null;
  accion: string;
  antes: JsonValor | null;
  despues: JsonValor | null;
  motivo: string | null;
}

/** GET /api/evaluaciones/{id}/traza (TrazaRespuesta). No incluye respuesta cruda ni verificación técnica. */
export interface Traza {
  evaluacion_id: IdNumerico;
  entrega_id: IdNumerico;
  estado: EstadoEvaluacion;
  nota: number | null;
  proveedor: string | null;
  modelo: string | null;
  temperatura: number | null;
  prompt_version: string | null;
  rubrica_version_id: IdNumerico | null;
  rubrica_version: number | null;
  eventos: EventoTraza[];
}

// ---------- Informe (RF-08) — InformeRespuesta del backend ----------

/** NivelDominio del backend; null cuando no hay datos suficientes. */
export type NivelDominio = "bajo" | "medio" | "alto";

/** Prioridades conocidas del plan; el backend envía `prioridad` como texto libre. */
export type Prioridad = "alta" | "media" | "baja";

export interface EstudianteResumen {
  /** UUID. */
  id: string;
  nombre: string | null;
}

/** LaboratorioInformeRespuesta: un laboratorio con evaluación publicada. */
export interface LaboratorioInforme {
  laboratorio_id: IdNumerico;
  codigo: string;
  titulo: string;
  /** Nombre de la cohorte ("Cohorte 1"). */
  cohorte: string;
  cohorte_numero: number;
  nota: number | null;
  evaluacion_id: IdNumerico;
  publicada_en: string | null;
}

/** PromedioCohorteRespuesta. */
export interface PromedioCohorte {
  cohorte: string;
  cohorte_numero: number;
  promedio: number | null;
  laboratorios_evaluados: number;
}

/** CompetenciaInformeRespuesta: `promedio` de 0 a 5. */
export interface CompetenciaInforme {
  competencia: string;
  promedio: number | null;
  nivel_dominio: NivelDominio | null;
  criterios_evaluados: number;
}

/** TematicaInformeRespuesta: `promedio` de 0 a 5. */
export interface TematicaInforme {
  tematica_id: IdNumerico;
  tematica: string;
  promedio: number | null;
  nivel_dominio: NivelDominio | null;
  criterios_evaluados: number;
}

/** EvolucionRespuesta (cohorte inicial → final). */
export interface Evolucion {
  cohorte_inicial: string;
  cohorte_final: string;
  promedio_inicial: number | null;
  promedio_final: number | null;
  diferencia: number | null;
}

/** AccionPlanRespuesta. */
export interface AccionPlan {
  accion: string;
  recurso: string;
  prioridad: string;
  competencia: string;
}

export type EstadoNarrativa = "generada" | "sin_datos" | "no_disponible" | "error";

/** NarrativaRespuesta: la redacta la IA; los números los pone el backend. */
export interface Narrativa {
  estado: EstadoNarrativa;
  mensaje: string | null;
  competencias_desarrolladas: string[];
  brechas: string[];
  plan_fortalecimiento: AccionPlan[];
  conclusion: string | null;
  generada_en: string | null;
}

/** GET /api/estudiantes/{id}/informe (InformeRespuesta). Solo evaluaciones publicadas. */
export interface Informe {
  estudiante: EstudianteResumen;
  laboratorios_evaluados: number;
  laboratorios: LaboratorioInforme[];
  promedios_cohorte: PromedioCohorte[];
  promedio_general: number | null;
  competencias: CompetenciaInforme[];
  tematicas: TematicaInforme[];
  evolucion: Evolucion | null;
  narrativa: Narrativa;
  avisos: string[];
}

// ---------- Mapa mental (RF-09) — MapaRespuesta del backend ----------

export type TipoNodo = "tematica" | "subtema" | "concepto" | "competencia" | "laboratorio";

/** EvidenciaMapaRespuesta. */
export interface EvidenciaMapa {
  fragmento: string;
  fuente: string;
  ubicacion: string | null;
  /** Código del laboratorio. */
  laboratorio: string;
  criterio_id: string;
}

/** NodoMapaRespuesta. Ids como "tematica:3", "concepto:3:perceptron", "lab:C1-01". */
export interface NodoMapa {
  id: string;
  tipo: TipoNodo;
  etiqueta: string;
  /** 0 a 5; en los laboratorios es su nota. */
  dominio: number | null;
  nivel_dominio: NivelDominio | null;
  evidencias: EvidenciaMapa[];
  aspectos_por_profundizar: string[];
  /** Códigos de laboratorio. */
  laboratorios: string[];
}

/** AristaMapaRespuesta: la jerarquía y las relaciones salen solo de aquí (no hay padre_id). */
export interface AristaMapa {
  origen: string;
  destino: string;
}

/** GET /api/estudiantes/{id}/mapa (MapaRespuesta). */
export interface Mapa {
  nodos: NodoMapa[];
  aristas: AristaMapa[];
  avisos: string[];
}

// ---------- Configuración de IA (RF-10) ----------

/** Proveedor tal como lo nombra el backend ("gemini" u "openai_compat"); la lista válida viene en proveedores_permitidos. */
export type ProveedorIA = string;

/** ActorRespuesta: quién guardó la configuración. */
export interface ActorConfigIA {
  id: string;
  nombre: string | null;
}

/** ClavesIARespuesta: solo dice si cada secreto está configurado en el servidor; nunca su valor. */
export interface ClavesIA {
  gemini_api_key_configurada: boolean;
  openai_compat_api_key_configurada: boolean;
  openai_compat_base_url_configurada: boolean;
}

/** ProveedorPermitido: modelos elegibles; los que no están en `modelos_probados` aún no se probaron con nuestros prompts. */
export interface ProveedorPermitido {
  proveedor: ProveedorIA;
  etiqueta: string;
  modelos: string[];
  modelos_probados: string[];
}

/** GET/PUT /api/config-ia (ConfigIARespuesta, solo admin). */
export interface ConfigIA {
  proveedor: ProveedorIA;
  modelo: string;
  temperatura: number;
  /** "entorno" = aún no se ha guardado desde el panel (valores por defecto del servidor). */
  origen: "base_de_datos" | "entorno";
  /** false = el modelo vigente ya no está en la lista permitida. */
  modelo_permitido: boolean;
  actualizado_por: ActorConfigIA | null;
  actualizado_en: string | null;
  temperatura_maxima: number;
  claves: ClavesIA;
  proveedores_permitidos: ProveedorPermitido[];
  /** Nombre del prompt → versión (solo lectura). */
  versiones_prompt: Record<string, string | null>;
}

/** Cuerpo de PUT /api/config-ia (ConfigIAEntrada): siempre los tres campos juntos. */
export interface ConfigIAEntrada {
  proveedor: ProveedorIA;
  modelo: string;
  temperatura: number;
}

/** POST /api/config-ia/probar (PruebaConexionRespuesta): siempre 200; el éxito lo dice `ok`. */
export interface ResultadoPruebaIA {
  ok: boolean;
  proveedor: ProveedorIA;
  modelo: string;
  /** null si no se llamó (falta la clave); igual al límite si se agotó el tiempo. */
  latencia_ms: number | null;
  mensaje: string;
}
