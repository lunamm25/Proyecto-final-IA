// Cliente único del API (contrato §11). Añade el JWT de Supabase y traduce los errores al español.
// Modo mock: si NEXT_PUBLIC_USAR_MOCKS=true o falta NEXT_PUBLIC_API_URL, responde con lib/mocks.ts.
// En modo mock el rol de /api/yo sale del email de la sesión: contiene "admin" → admin,
// contiene "docente" → docente; cualquier otro → estudiante.
import {
  cohortesMock,
  configIAMock,
  entregasMock,
  evaluacionesMock,
  informeMock,
  informeNarrativaErrorMock,
  informeSinPublicadasMock,
  laboratoriosSinRubricaMock,
  mapaConAvisosMock,
  mapaMock,
  mapaVacioMock,
  MODELO_FALLA_MOCK,
  perfilesMock,
  rubricaExtraidaMock,
  resultadoSimuladoMock,
  rubricaVersionMock,
  trazaMock,
  usuariosMock,
} from "@/lib/mocks";
import { calcularInconsistencias } from "@/lib/inconsistencias-rubrica";
import { leerSesionMock } from "@/lib/sesion-mock";
import { obtenerSupabaseNavegador } from "@/lib/supabase/cliente";
import type {
  AjusteCriterio,
  CambioRol,
  Cohorte,
  ConfigIA,
  ConfigIAEntrada,
  Entrega,
  ErrorRespuesta,
  Evaluacion,
  EstadoEvaluacion,
  EvaluacionResumen,
  FiltrosEvaluaciones,
  IdNumerico,
  Informe,
  JsonValor,
  Laboratorio,
  LaboratorioEntrada,
  ListadoEstudiantes,
  ListadoEvaluaciones,
  Mapa,
  NuevaEntrega,
  Perfil,
  RespuestaEvaluar,
  ResultadoExtraccion,
  ResultadoPruebaIA,
  ResultadoValidacion,
  Retroalimentacion,
  RetroalimentacionCriterioEntrada,
  RetroalimentacionEntrada,
  Rol,
  Rubrica,
  RubricaVersion,
  Traza,
  Usuario,
} from "@/lib/tipos";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");

export const MODO_MOCK = process.env.NEXT_PUBLIC_USAR_MOCKS === "true" || API_URL === "";

export class ErrorApi extends Error {
  readonly status: number;
  /** Lista de inconsistencias que el backend envía en el 422 de rúbricas (ErrorRubricaRespuesta). */
  readonly inconsistencias: string[];

  constructor(status: number, mensaje: string, inconsistencias: string[] = []) {
    super(mensaje);
    this.name = "ErrorApi";
    this.status = status;
    this.inconsistencias = inconsistencias;
  }
}

/** Extrae `inconsistencias: string[]` del cuerpo de error, si viene. */
function inconsistenciasDe(cuerpo: unknown): string[] {
  if (typeof cuerpo !== "object" || cuerpo === null || !("inconsistencias" in cuerpo)) return [];
  const lista: unknown = cuerpo.inconsistencias;
  return Array.isArray(lista) ? lista.filter((item): item is string => typeof item === "string") : [];
}

/** Convierte cualquier error en un mensaje en español para mostrar al usuario. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ErrorApi) return error.message;
  return "Ocurrió un error inesperado. Intenta de nuevo.";
}

const MENSAJES_POR_ESTADO: Record<number, string> = {
  400: "La solicitud no es válida. Revisa los datos enviados.",
  401: "Tu sesión expiró o no has iniciado sesión. Vuelve a ingresar.",
  403: "No tienes permiso para realizar esta acción.",
  404: "No se encontró el recurso solicitado.",
  409: "La operación entra en conflicto con el estado actual. Recarga la página.",
  413: "El archivo es demasiado grande.",
  422: "Los datos enviados no son válidos.",
};

function esErrorRespuesta(valor: unknown): valor is ErrorRespuesta {
  return typeof valor === "object" && valor !== null && "detail" in valor;
}

/** 403: siempre empieza con "No tienes permiso…" y, si el backend da más contexto, lo añade. */
function mensajeSinPermiso(detalle: string): string {
  const base = MENSAJES_POR_ESTADO[403];
  if (detalle === "" || detalle.toLowerCase().startsWith("no tienes permiso")) return base;
  return `${base} ${detalle}`;
}

function mensajePorEstado(status: number, cuerpo: unknown): string {
  if (status >= 500) return "El servidor tuvo un problema. Intenta de nuevo en unos minutos.";
  const base = MENSAJES_POR_ESTADO[status] ?? `Error inesperado del servidor (código ${status}).`;
  if (!esErrorRespuesta(cuerpo)) return base;
  if (status === 403) return mensajeSinPermiso(typeof cuerpo.detail === "string" ? cuerpo.detail.trim() : "");
  if (typeof cuerpo.detail === "string" && cuerpo.detail.trim() !== "") return cuerpo.detail;
  if (Array.isArray(cuerpo.detail) && cuerpo.detail.length > 0) {
    return `${base} ${cuerpo.detail.map((d) => d.msg).join("; ")}`;
  }
  return base;
}

async function obtenerToken(): Promise<string | null> {
  const supabase = obtenerSupabaseNavegador();
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

type Metodo = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/** Límite de espera de las peticiones que generan IA en el momento (informe y mapa). */
export const TIEMPO_ESPERA_GENERACION_MS = 60_000;

export const MENSAJE_TIEMPO_AGOTADO =
  "La generación tardó más de un minuto y se canceló. Puede que el servidor siga trabajando: intenta de nuevo.";

/** Límite de espera de una petición y el mensaje que se muestra si se agota. */
interface LimiteEspera {
  ms: number;
  mensaje: string;
}

const LIMITE_GENERACION: LimiteEspera = { ms: TIEMPO_ESPERA_GENERACION_MS, mensaje: MENSAJE_TIEMPO_AGOTADO };

/** Ejecuta `fetch` con límite de tiempo opcional: si se agota, aborta y lanza un 408 con mensaje claro. */
async function fetchConLimite(url: string, opciones: RequestInit, limite?: LimiteEspera): Promise<Response> {
  if (limite === undefined) return fetch(url, opciones);
  const controlador = new AbortController();
  const temporizador = setTimeout(() => controlador.abort(), limite.ms);
  try {
    return await fetch(url, { ...opciones, signal: controlador.signal });
  } catch (causa) {
    if (controlador.signal.aborted) throw new ErrorApi(408, limite.mensaje);
    throw causa;
  } finally {
    clearTimeout(temporizador);
  }
}

async function enviar(metodo: Metodo, ruta: string, cuerpo?: unknown, limite?: LimiteEspera): Promise<Response> {
  const cabeceras = new Headers({ Accept: "application/json" });
  const token = await obtenerToken();
  if (token) cabeceras.set("Authorization", `Bearer ${token}`);

  let body: BodyInit | undefined;
  if (cuerpo instanceof FormData) {
    body = cuerpo;
  } else if (cuerpo !== undefined) {
    cabeceras.set("Content-Type", "application/json");
    body = JSON.stringify(cuerpo);
  }

  let respuesta: Response;
  try {
    respuesta = await fetchConLimite(`${API_URL}/api${ruta}`, { method: metodo, headers: cabeceras, body }, limite);
  } catch (causa) {
    if (causa instanceof ErrorApi) throw causa;
    throw new ErrorApi(0, "No se pudo conectar con el servidor. Revisa tu conexión a internet.");
  }

  if (!respuesta.ok) {
    const datos: unknown = await respuesta.json().catch(() => null);
    if (respuesta.status === 401) cerrarSesionExpirada();
    throw new ErrorApi(respuesta.status, mensajePorEstado(respuesta.status, datos), inconsistenciasDe(datos));
  }
  return respuesta;
}

/** Parámetro de /login que indica que se llegó ahí porque la sesión expiró o el token no es válido. */
export const MOTIVO_SESION_EXPIRADA = "sesion-expirada";

let manejadorSesionExpirada: (() => void) | null = null;

/** El proveedor de sesión registra aquí qué hacer ante un 401 (cerrar sesión e ir a /login). */
export function registrarManejadorSesionExpirada(manejador: (() => void) | null): void {
  manejadorSesionExpirada = manejador;
}

/** 401 del backend (sin token o token inválido): delega en el manejador registrado. */
function cerrarSesionExpirada(): void {
  manejadorSesionExpirada?.();
}

async function peticion<T>(metodo: Metodo, ruta: string, cuerpo?: unknown, limite?: LimiteEspera): Promise<T> {
  const respuesta = await enviar(metodo, ruta, cuerpo, limite);
  return (await respuesta.json()) as T;
}

async function peticionSinContenido(metodo: Metodo, ruta: string, cuerpo?: unknown): Promise<void> {
  await enviar(metodo, ruta, cuerpo);
}

// ---------- Utilidades del modo mock ----------

function esperar(ms = 300): Promise<void> {
  return new Promise((resolver) => setTimeout(resolver, ms));
}

async function simulado<T>(producir: () => T): Promise<T> {
  await esperar();
  return structuredClone(producir());
}

export function rolSimuladoPorEmail(email: string): Rol {
  const minusculas = email.toLowerCase();
  if (minusculas.includes("admin")) return "admin";
  if (minusculas.includes("docente")) return "docente";
  return "estudiante";
}

async function emailDeSesion(): Promise<string | null> {
  const supabase = obtenerSupabaseNavegador();
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    return data.session?.user.email ?? null;
  }
  return leerSesionMock();
}

/** Ids numéricos nuevos del mock (como los autoincrementales de Postgres). */
let siguienteIdMock = 1000;
function nuevoIdMock(): IdNumerico {
  siguienteIdMock += 1;
  return siguienteIdMock;
}

const estadoMock = {
  cohortes: structuredClone(cohortesMock),
  entregas: structuredClone(entregasMock),
  evaluaciones: structuredClone(evaluacionesMock),
  usuarios: structuredClone(usuariosMock),
  config: structuredClone(configIAMock),
  rubricas: rubricasInicialesMock(),
};

/** Versión vigente por laboratorio (en memoria); los de `laboratoriosSinRubricaMock` empiezan sin rúbrica. */
function rubricasInicialesMock(): Record<IdNumerico, RubricaVersion> {
  const vigentes: Record<IdNumerico, RubricaVersion> = {};
  cohortesMock
    .flatMap((cohorte) => cohorte.laboratorios)
    .filter((lab) => !laboratoriosSinRubricaMock.includes(lab.id))
    .forEach((lab) => {
      vigentes[lab.id] = { ...structuredClone(rubricaVersionMock), id: 100 + lab.id };
    });
  return vigentes;
}

/** GET /cohortes del mock: añade `version_rubrica_vigente` como hace el backend. */
function cohortesConVersionMock(): Cohorte[] {
  return estadoMock.cohortes.map((cohorte) => ({
    ...cohorte,
    laboratorios: cohorte.laboratorios.map((lab) => ({
      ...lab,
      version_rubrica_vigente: estadoMock.rubricas[lab.id]?.version ?? null,
    })),
  }));
}

function noEncontrado(): ErrorApi {
  return new ErrorApi(404, MENSAJES_POR_ESTADO[404]);
}

function existeLaboratorioMock(id: IdNumerico): boolean {
  return estadoMock.cohortes.some((cohorte) => cohorte.laboratorios.some((l) => l.id === id));
}

function rubricaVigenteMock(laboratorioId: IdNumerico): RubricaVersion {
  const vigente = estadoMock.rubricas[laboratorioId];
  if (!existeLaboratorioMock(laboratorioId) || !vigente) {
    throw new ErrorApi(404, "Este laboratorio aún no tiene una rúbrica vigente.");
  }
  return vigente;
}

function guardarVersionMock(laboratorioId: IdNumerico, rubrica: Rubrica): RubricaVersion {
  if (!existeLaboratorioMock(laboratorioId)) throw noEncontrado();
  const { inconsistencias } = validarRubricaMock(rubrica);
  if (inconsistencias.length > 0) {
    throw new ErrorApi(422, "La rúbrica tiene inconsistencias y no se puede aprobar.", inconsistencias);
  }
  const anterior = estadoMock.rubricas[laboratorioId];
  const nueva: RubricaVersion = {
    id: nuevoIdMock(),
    version: (anterior?.version ?? 0) + 1,
    contenido: structuredClone(rubrica),
    estado: "aprobada",
    creada_por: perfilesMock.docente.id,
    creada_en: new Date().toISOString(),
  };
  estadoMock.rubricas[laboratorioId] = nueva;
  return nueva;
}

function validarCodigoUnicoMock(datos: LaboratorioEntrada, idActual: IdNumerico | null): void {
  const cohorte = estadoMock.cohortes.find((c) => c.id === datos.cohorte_id);
  if (!cohorte) throw noEncontrado();
  const codigo = datos.codigo.trim().toLowerCase();
  if (cohorte.laboratorios.some((l) => l.id !== idActual && l.codigo.trim().toLowerCase() === codigo)) {
    throw new ErrorApi(409, `Ya existe un laboratorio con el código ${datos.codigo} en esta cohorte.`);
  }
}

/** Validación aproximada de POST /api/entregas solo para el modo mock; la oficial la hace el backend. */
function validarEntregaMock(datos: NuevaEntrega): void {
  if (!datos.pdf.name.toLowerCase().endsWith(".pdf")) {
    throw new ErrorApi(422, "El informe debe ser un archivo PDF.");
  }
  if (Boolean(datos.zip) === Boolean(datos.github_url)) {
    throw new ErrorApi(422, "Debes enviar el código como ZIP o como URL de GitHub (solo una de las dos).");
  }
}

// ---------- Evaluaciones en modo mock ----------
// Simula el pipeline (RNF-04): tras evaluarEntrega la evaluación queda en estado "procesando"
// durante DURACION_PROCESO_MOCK_MS y luego pasa a "borrador" con `resultadoSimuladoMock`.
// Las transiciones imitan services/revision.py del backend: revisar (borrador → en_revision),
// aprobar (en_revision → aprobada), publicar (aprobada → publicada); ajustes y retroalimentación solo en
// borrador o en_revision. La nota NUNCA se calcula aquí: es un valor fijo del mock (la recalcula el backend).

const DURACION_PROCESO_MOCK_MS = 9000;

/** Momento (ms) en que termina el procesamiento simulado de cada evaluación en curso. */
const finProcesoMock: Record<IdNumerico, number> = {};

const trazasMock: Record<IdNumerico, Traza> = { [trazaMock.evaluacion_id]: structuredClone(trazaMock) };

async function perfilMockActual(): Promise<Perfil> {
  return perfilesMock[rolSimuladoPorEmail((await emailDeSesion()) ?? "")];
}

function buscarEvaluacionMock(id: IdNumerico): Evaluacion {
  const evaluacion = estadoMock.evaluaciones.find((e) => e.id === id);
  if (!evaluacion) throw noEncontrado();
  avanzarProcesoMock(evaluacion);
  return evaluacion;
}

/** La evaluación del backend no trae laboratorio ni estudiante: el mock los saca de su entrega. */
function entregaDeEvaluacionMock(evaluacion: Evaluacion): Entrega | undefined {
  return estadoMock.entregas.find((e) => e.id === evaluacion.entrega_id);
}

function sincronizarResumenMock(evaluacion: Evaluacion): void {
  const entrega = entregaDeEvaluacionMock(evaluacion);
  if (entrega?.evaluacion?.id !== evaluacion.id) return;
  entrega.evaluacion = { id: evaluacion.id, estado: evaluacion.estado, nota: evaluacion.nota };
}

function avanzarProcesoMock(evaluacion: Evaluacion): void {
  const fin = finProcesoMock[evaluacion.id];
  if (fin === undefined || Date.now() < fin) return;
  Object.assign(evaluacion, structuredClone(resultadoSimuladoMock), { estado: "borrador" });
  delete finProcesoMock[evaluacion.id];
  registrarEventoMock(evaluacion, null, {
    accion: "evaluacion_completada",
    antes: { estado: "procesando" },
    despues: { estado: "borrador" },
    motivo: null,
  });
  sincronizarResumenMock(evaluacion);
}

function crearEvaluacionEnProcesoMock(entrega: Entrega, perfil: Perfil): Evaluacion {
  const { config } = estadoMock;
  const version = estadoMock.rubricas[entrega.laboratorio_id];
  const evaluacion: Evaluacion = {
    id: nuevoIdMock(),
    entrega_id: entrega.id,
    estado: "procesando",
    nota: null,
    rubrica_version_id: version?.id ?? null,
    rubrica_version: version?.version ?? null,
    proveedor: config.proveedor,
    modelo: config.modelo,
    temperatura: config.temperatura,
    prompt_version: "evaluacion-v1",
    error: null,
    criterios: [],
    retroalimentacion: null,
    retroalimentacion_ia: null,
    creada_en: new Date().toISOString(),
    aprobada_en: null,
    publicada_en: null,
  };
  estadoMock.evaluaciones.push(evaluacion);
  finProcesoMock[evaluacion.id] = Date.now() + DURACION_PROCESO_MOCK_MS;
  registrarEventoMock(evaluacion, perfil, {
    accion: "lanzar_evaluacion",
    antes: null,
    despues: { estado: "procesando" },
    motivo: null,
  });
  return evaluacion;
}

/** Como el backend: el estudiante solo ve sus evaluaciones publicadas (404 si no es suya o no está publicada). */
function verificarAccesoEstudianteMock(evaluacion: Evaluacion, estudianteId: string): void {
  if (entregaDeEvaluacionMock(evaluacion)?.estudiante_id !== estudianteId) throw noEncontrado();
  if (evaluacion.estado !== "publicada") throw noEncontrado();
}

/**
 * Lo que el backend oculta al estudiante: datos del modelo, nivel original de la IA, textos originales
 * (original_ia, retroalimentacion_ia) y el motivo del ajuste docente.
 */
function vistaEstudianteMock(evaluacion: Evaluacion): Evaluacion {
  return {
    ...evaluacion,
    proveedor: null,
    modelo: null,
    temperatura: null,
    prompt_version: null,
    retroalimentacion_ia: null,
    criterios: evaluacion.criterios.map((criterio) => ({
      ...criterio,
      nivel_ia: null,
      original_ia: null,
      ajuste_docente: null,
    })),
  };
}

function trazaDeEvaluacionMock(evaluacion: Evaluacion): Traza {
  const existente = trazasMock[evaluacion.id] ?? { eventos: [] };
  const traza: Traza = {
    evaluacion_id: evaluacion.id,
    entrega_id: evaluacion.entrega_id,
    estado: evaluacion.estado,
    nota: evaluacion.nota,
    proveedor: evaluacion.proveedor,
    modelo: evaluacion.modelo,
    temperatura: evaluacion.temperatura,
    prompt_version: evaluacion.prompt_version,
    rubrica_version_id: evaluacion.rubrica_version_id,
    rubrica_version: evaluacion.rubrica_version,
    eventos: existente.eventos,
  };
  trazasMock[evaluacion.id] = traza;
  return traza;
}

interface CambioAuditado {
  accion: string;
  antes: JsonValor | null;
  despues: JsonValor | null;
  motivo: string | null;
}

/** `perfil` null = acción del sistema (como `usuario: null` en el backend). */
function registrarEventoMock(evaluacion: Evaluacion, perfil: Perfil | null, cambio: CambioAuditado): void {
  trazaDeEvaluacionMock(evaluacion).eventos.push({
    id: nuevoIdMock(),
    fecha: new Date().toISOString(),
    usuario: perfil ? { id: perfil.id, nombre: perfil.nombre } : null,
    ...cambio,
  });
}

function exigirEditableMock(evaluacion: Evaluacion, que: string): void {
  if (evaluacion.estado !== "borrador" && evaluacion.estado !== "en_revision") {
    throw new ErrorApi(409, `No se puede ${que} una evaluación en estado '${evaluacion.estado}'.`);
  }
}

/** Ajuste del modo mock: actualiza el nivel y la traza. La nota queda igual (el recálculo es del backend). */
function ajustarCriterioMock(id: IdNumerico, criterioId: string, ajuste: AjusteCriterio, perfil: Perfil): Evaluacion {
  if (ajuste.motivo.trim() === "") throw new ErrorApi(422, "El motivo del ajuste es obligatorio.");
  const evaluacion = buscarEvaluacionMock(id);
  exigirEditableMock(evaluacion, "ajustar");
  const criterio = evaluacion.criterios.find((c) => c.criterio_id === criterioId);
  if (!criterio) throw new ErrorApi(404, `El criterio '${criterioId}' no existe en esta evaluación.`);
  const laboratorioId = entregaDeEvaluacionMock(evaluacion)?.laboratorio_id;
  const niveles = laboratorioId === undefined ? undefined
    : estadoMock.rubricas[laboratorioId]?.contenido.criterios.find((c) => c.id === criterioId)?.niveles;
  if (!niveles?.some((n) => n.nombre === ajuste.nivel_final)) {
    throw new ErrorApi(422, `El nivel '${ajuste.nivel_final}' no existe en el criterio '${criterioId}'.`);
  }
  const antes = { criterio_id: criterioId, nivel_final: criterio.nivel_final };
  criterio.nivel_final = ajuste.nivel_final;
  criterio.ajuste_docente = ajuste.motivo.trim();
  registrarEventoMock(evaluacion, perfil, {
    accion: "ajustar_criterio",
    antes,
    despues: { criterio_id: criterioId, nivel_final: ajuste.nivel_final },
    motivo: criterio.ajuste_docente,
  });
  sincronizarResumenMock(evaluacion);
  return evaluacion;
}

const CAMPOS_RETRO_CRITERIO = ["justificacion", "fortalezas", "debilidades", "recomendacion"] as const;
const CAMPOS_RETRO_GENERAL = [
  "retroalimentacion_general",
  "como_aplico_conocimientos",
  "aprendizajes_identificados",
  "aspectos_a_fortalecer",
] as const;

const RETRO_VACIA: Retroalimentacion = {
  aprendizajes_identificados: [],
  como_aplico_conocimientos: null,
  aspectos_a_fortalecer: [],
  retroalimentacion_general: null,
};

/** Campos cambiados de una edición, separados en editados (texto nuevo) y restablecidos (null = texto de la IA). */
interface ResumenEdicion {
  editados: string[];
  restablecidos: string[];
}

/** Aplica la edición de un criterio: valor = texto nuevo; null = vuelve a `original_ia`; omitido = sin cambios. */
function aplicarRetroCriterioMock(evaluacion: Evaluacion, edicion: RetroalimentacionCriterioEntrada, resumen: ResumenEdicion): void {
  const criterio = evaluacion.criterios.find((c) => c.criterio_id === edicion.criterio_id);
  if (!criterio) throw new ErrorApi(404, `El criterio '${edicion.criterio_id}' no existe en esta evaluación.`);
  const original = criterio.original_ia;
  for (const campo of CAMPOS_RETRO_CRITERIO) {
    const valor = edicion[campo];
    if (valor === undefined) continue;
    const etiqueta = `${edicion.criterio_id}.${campo}`;
    if (valor === null) resumen.restablecidos.push(etiqueta);
    else resumen.editados.push(etiqueta);
    if (campo === "fortalezas" || campo === "debilidades") {
      criterio[campo] = valor === null ? (original?.[campo] ?? []) : (valor as string[]);
    } else {
      criterio[campo] = valor === null ? (original?.[campo] ?? null) : (valor as string);
    }
  }
}

/** Aplica la edición general: valor = texto nuevo; null = vuelve a `retroalimentacion_ia`; omitido = sin cambios. */
function aplicarRetroGeneralMock(evaluacion: Evaluacion, entrada: RetroalimentacionEntrada, resumen: ResumenEdicion): void {
  const original = evaluacion.retroalimentacion_ia ?? RETRO_VACIA;
  const nueva: Retroalimentacion = { ...(evaluacion.retroalimentacion ?? RETRO_VACIA) };
  for (const campo of CAMPOS_RETRO_GENERAL) {
    const valor = entrada[campo];
    if (valor === undefined) continue;
    if (valor === null) resumen.restablecidos.push(campo);
    else resumen.editados.push(campo);
    if (campo === "aprendizajes_identificados" || campo === "aspectos_a_fortalecer") {
      nueva[campo] = valor === null ? original[campo] : (valor as string[]);
    } else {
      nueva[campo] = valor === null ? original[campo] : (valor as string);
    }
  }
  evaluacion.retroalimentacion = nueva;
}

/** Edición de textos del modo mock: cambia los textos finales; los originales de la IA se conservan y se pueden restablecer. */
function editarRetroalimentacionMock(id: IdNumerico, entrada: RetroalimentacionEntrada, perfil: Perfil): Evaluacion {
  const criterios = entrada.criterios ?? [];
  const hayGeneral = CAMPOS_RETRO_GENERAL.some((campo) => entrada[campo] !== undefined);
  if (!hayGeneral && criterios.length === 0) {
    throw new ErrorApi(422, "Indica al menos un texto de retroalimentación para editar.");
  }
  const evaluacion = buscarEvaluacionMock(id);
  exigirEditableMock(evaluacion, "editar la retroalimentación de");
  const resumen: ResumenEdicion = { editados: [], restablecidos: [] };
  if (hayGeneral) aplicarRetroGeneralMock(evaluacion, entrada, resumen);
  criterios.forEach((edicion) => aplicarRetroCriterioMock(evaluacion, edicion, resumen));
  registrarEventoMock(evaluacion, perfil, {
    accion: resumen.editados.length === 0 ? "restablecer_retroalimentacion" : "editar_retroalimentacion",
    antes: null,
    despues: { editados: resumen.editados, restablecidos_a_la_ia: resumen.restablecidos },
    motivo: entrada.motivo ?? null,
  });
  return evaluacion;
}

type AccionEstado = "revisar" | "aprobar" | "publicar";

const TRANSICIONES_MOCK: Record<AccionEstado, { desde: EstadoEvaluacion; hasta: EstadoEvaluacion; verbo: string }> = {
  revisar: { desde: "borrador", hasta: "en_revision", verbo: "pasar a revisión" },
  aprobar: { desde: "en_revision", hasta: "aprobada", verbo: "aprobar" },
  publicar: { desde: "aprobada", hasta: "publicada", verbo: "publicar" },
};

function cambiarEstadoMock(id: IdNumerico, accion: AccionEstado, perfil: Perfil): Evaluacion {
  const evaluacion = buscarEvaluacionMock(id);
  const { desde, hasta, verbo } = TRANSICIONES_MOCK[accion];
  if (evaluacion.estado !== desde) {
    throw new ErrorApi(409, `No se puede ${verbo} una evaluación en estado '${evaluacion.estado}'.`);
  }
  evaluacion.estado = hasta;
  const ahora = new Date().toISOString();
  if (hasta === "aprobada") evaluacion.aprobada_en = ahora;
  if (hasta === "publicada") evaluacion.publicada_en = ahora;
  registrarEventoMock(evaluacion, perfil, { accion, antes: { estado: desde }, despues: { estado: hasta }, motivo: null });
  sincronizarResumenMock(evaluacion);
  return evaluacion;
}

/** GET /evaluaciones del modo mock: arma EvaluacionResumen con la entrega, el laboratorio y el estudiante. */
function resumenEvaluacionMock(evaluacion: Evaluacion): EvaluacionResumen {
  const entrega = entregaDeEvaluacionMock(evaluacion);
  const laboratorio = estadoMock.cohortes.flatMap((c) => c.laboratorios).find((l) => l.id === entrega?.laboratorio_id);
  const estudiante = estadoMock.usuarios.find((u) => u.id === entrega?.estudiante_id);
  return {
    id: evaluacion.id,
    entrega_id: evaluacion.entrega_id,
    estudiante: { id: entrega?.estudiante_id ?? "", nombre: estudiante?.nombre ?? null },
    laboratorio: { id: laboratorio?.id ?? 0, codigo: laboratorio?.codigo ?? "", titulo: laboratorio?.titulo ?? "" },
    estado: evaluacion.estado,
    nota: evaluacion.nota,
    creada_en: evaluacion.creada_en,
    aprobada_en: evaluacion.aprobada_en,
    publicada_en: evaluacion.publicada_en,
  };
}

/** GET /estudiantes del modo mock: `laboratorios_evaluados` lo calcularía el backend; aquí se simula igual. */
function listarEstudiantesMock(limit: number, offset: number): ListadoEstudiantes {
  const filas = estadoMock.usuarios
    .filter((u) => u.rol === "estudiante")
    .map((u) => {
      const publicadas = estadoMock.entregas.filter((e) => e.estudiante_id === u.id && e.evaluacion?.estado === "publicada");
      return { id: u.id, nombre: u.nombre, correo: u.correo, laboratorios_evaluados: new Set(publicadas.map((e) => e.laboratorio_id)).size };
    })
    .sort((a, b) => (a.nombre ?? "").localeCompare(b.nombre ?? ""));
  return { items: filas.slice(offset, offset + limit), total: filas.length, limit, offset };
}

function listarEvaluacionesMock(filtros: FiltrosEvaluaciones): ListadoEvaluaciones {
  const limit = filtros.limit ?? LIMITE_EVALUACIONES_POR_DEFECTO;
  const offset = filtros.offset ?? 0;
  estadoMock.evaluaciones.forEach(avanzarProcesoMock);
  const filas = estadoMock.evaluaciones
    .map(resumenEvaluacionMock)
    .filter((fila) => !filtros.estado || fila.estado === filtros.estado)
    .filter((fila) => filtros.laboratorio_id === undefined || fila.laboratorio.id === filtros.laboratorio_id)
    .filter((fila) => !filtros.estudiante_id || fila.estudiante.id === filtros.estudiante_id)
    .sort((a, b) => b.creada_en.localeCompare(a.creada_en));
  return { items: filas.slice(offset, offset + limit), total: filas.length, limit, offset };
}
// ---------- Usuarios y configuración de IA en modo mock ----------
// Reglas aproximadas solo para el modo mock; la seguridad real la aplica el backend.

const ROLES_GESTION_MOCK: Rol[] = ["docente", "admin"];
/** Usuarios y configuración de IA: solo admin (como requiere_rol("admin") en el backend). */
const ROLES_SOLO_ADMIN_MOCK: Rol[] = ["admin"];
const ROLES_CONFIG_IA_MOCK = ROLES_SOLO_ADMIN_MOCK;
const ROLES_VALIDOS_MOCK: Rol[] = ["estudiante", "docente", "admin"];
const TEMPERATURA_MAXIMA_MOCK = 0.2;

async function exigirRolMock(roles: Rol[]): Promise<Perfil> {
  const email = await emailDeSesion();
  if (!email) throw new ErrorApi(401, MENSAJES_POR_ESTADO[401]);
  const perfil = perfilesMock[rolSimuladoPorEmail(email)];
  if (!roles.includes(perfil.rol)) throw new ErrorApi(403, MENSAJES_POR_ESTADO[403]);
  return perfil;
}

/** Como services/usuarios.py: lista ordenada por nombre (sin distinguir mayúsculas), los sin nombre al final. */
function usuariosOrdenadosMock(): Usuario[] {
  return [...estadoMock.usuarios].sort((a, b) => {
    if (a.nombre === null || b.nombre === null) return a.nombre === null ? (b.nombre === null ? 0 : 1) : -1;
    return a.nombre.toLowerCase().localeCompare(b.nombre.toLowerCase());
  });
}

/**
 * Cambio de rol del modo mock con las mismas reglas y mensajes del backend:
 * 422 rol no válido, 404 usuario inexistente, mismo rol → sin cambios (200), 409 si un admin se quita su propio
 * rol de administrador o si el sistema quedaría sin administradores.
 */
function cambiarRolMock(usuarioId: string, rol: string, perfil: Perfil): Usuario {
  if (!ROLES_VALIDOS_MOCK.some((valido) => valido === rol)) {
    throw new ErrorApi(422, "Rol no válido. Usa: estudiante, docente o admin.");
  }
  const usuario = estadoMock.usuarios.find((u) => u.id === usuarioId);
  if (!usuario) throw new ErrorApi(404, "El usuario no existe.");
  if (usuario.rol === rol) return usuario;
  if (usuario.rol === "admin") {
    if (usuario.id === perfil.id) {
      throw new ErrorApi(409, "No puedes quitarte tu propio rol de administrador. Pide a otro administrador que lo haga.");
    }
    if (estadoMock.usuarios.filter((u) => u.rol === "admin").length <= 1) {
      throw new ErrorApi(409, "No se puede cambiar el rol: el sistema debe tener al menos un administrador.");
    }
  }
  usuario.rol = rol as Rol;
  return usuario;
}

/** Como el backend: proveedor y modelo de la lista permitida, temperatura 0–0,2; si no cambia nada, 200 sin auditar. */
function guardarConfigMock(datos: ConfigIAEntrada, perfil: Perfil): ConfigIA {
  const { config } = estadoMock;
  const permitido = config.proveedores_permitidos.find((p) => p.proveedor === datos.proveedor);
  if (!permitido) throw new ErrorApi(422, "Proveedor de IA no válido. Usa: gemini u openai_compat.");
  if (!permitido.modelos.includes(datos.modelo)) {
    throw new ErrorApi(422, `El modelo '${datos.modelo}' no está permitido para ${permitido.etiqueta}.`);
  }
  if (!(datos.temperatura >= 0 && datos.temperatura <= TEMPERATURA_MAXIMA_MOCK)) {
    throw new ErrorApi(422, "La temperatura debe estar entre 0 y 0,2.");
  }
  const igual = config.proveedor === datos.proveedor && config.modelo === datos.modelo && config.temperatura === datos.temperatura;
  if (igual) return config;
  estadoMock.config = {
    ...config,
    proveedor: datos.proveedor,
    modelo: datos.modelo,
    temperatura: datos.temperatura,
    origen: "base_de_datos",
    modelo_permitido: true,
    actualizado_por: { id: perfil.id, nombre: perfil.nombre },
    actualizado_en: new Date().toISOString(),
  };
  return estadoMock.config;
}

/** Demora simulada de la prueba (el backend tarda hasta ~10 s). */
const DEMORA_PRUEBA_MOCK_MS = 2500;

/** Simula POST /config-ia/probar sobre la configuración guardada: siempre "200"; falla con MODELO_FALLA_MOCK. */
function probarConfigMock(): ResultadoPruebaIA {
  const { proveedor, modelo } = estadoMock.config;
  if (modelo === MODELO_FALLA_MOCK) {
    return {
      ok: false,
      proveedor,
      modelo,
      latencia_ms: null,
      mensaje: "No se pudo conectar con el proveedor de IA. Revisa que el servicio esté disponible y que la clave esté configurada.",
    };
  }
  return { ok: true, proveedor, modelo, latencia_ms: 842, mensaje: "Conexión correcta con el proveedor de IA." };
}

/**
 * Validación del modo mock con la misma lógica del editor; la validación oficial la hace el backend.
 * Devuelve textos, como ValidacionRubricaRespuesta del backend.
 */
function validarRubricaMock(rubrica: Rubrica): ResultadoValidacion {
  const inconsistencias = calcularInconsistencias(rubrica).map((inconsistencia) => inconsistencia.mensaje);
  return { valida: inconsistencias.length === 0, inconsistencias };
}

// ---------- Usuarios ----------

export async function obtenerYo(): Promise<Perfil> {
  if (MODO_MOCK) {
    const email = await emailDeSesion();
    if (!email) throw new ErrorApi(401, MENSAJES_POR_ESTADO[401]);
    return simulado(() => ({ ...perfilesMock[rolSimuladoPorEmail(email)], email }));
  }
  return peticion<Perfil>("GET", "/yo");
}

/** GET /usuarios (solo admin): id, nombre, correo y rol, ordenados por nombre. */
export async function listarUsuarios(): Promise<Usuario[]> {
  if (MODO_MOCK) {
    await exigirRolMock(ROLES_SOLO_ADMIN_MOCK);
    return simulado(usuariosOrdenadosMock);
  }
  return peticion<Usuario[]>("GET", "/usuarios");
}

/** PATCH /usuarios/{id}/rol (solo admin) con motivo opcional, que queda en la auditoría. */
export async function cambiarRol(usuarioId: string, rol: Rol, motivo?: string): Promise<Usuario> {
  const motivoLimpio = motivo?.trim();
  const cuerpo: CambioRol = motivoLimpio ? { rol, motivo: motivoLimpio } : { rol };
  if (MODO_MOCK) {
    const perfil = await exigirRolMock(ROLES_SOLO_ADMIN_MOCK);
    return simulado(() => cambiarRolMock(usuarioId, cuerpo.rol, perfil));
  }
  return peticion<Usuario>("PATCH", `/usuarios/${encodeURIComponent(usuarioId)}/rol`, cuerpo);
}

// ---------- Cohortes y laboratorios ----------

export async function listarCohortes(): Promise<Cohorte[]> {
  if (MODO_MOCK) return simulado(cohortesConVersionMock);
  return peticion<Cohorte[]>("GET", "/cohortes");
}

export async function crearLaboratorio(datos: LaboratorioEntrada): Promise<Laboratorio> {
  if (MODO_MOCK) {
    return simulado(() => {
      validarCodigoUnicoMock(datos, null);
      const laboratorio: Laboratorio = { ...datos, id: nuevoIdMock() };
      estadoMock.cohortes.find((c) => c.id === datos.cohorte_id)?.laboratorios.push(laboratorio);
      return laboratorio;
    });
  }
  return peticion<Laboratorio>("POST", "/laboratorios", datos);
}

/** En modo mock, si cambia la cohorte el laboratorio se mueve a la nueva cohorte. */
function actualizarLaboratorioMock(id: IdNumerico, datos: LaboratorioEntrada): Laboratorio {
  if (!existeLaboratorioMock(id)) throw noEncontrado();
  validarCodigoUnicoMock(datos, id);
  const laboratorio: Laboratorio = { ...datos, id };
  estadoMock.cohortes.forEach((cohorte) => {
    cohorte.laboratorios = cohorte.laboratorios.filter((l) => l.id !== id || cohorte.id === datos.cohorte_id);
    const indice = cohorte.laboratorios.findIndex((l) => l.id === id);
    if (indice >= 0) cohorte.laboratorios[indice] = laboratorio;
    else if (cohorte.id === datos.cohorte_id) cohorte.laboratorios.push(laboratorio);
  });
  return laboratorio;
}

export async function actualizarLaboratorio(id: IdNumerico, datos: LaboratorioEntrada): Promise<Laboratorio> {
  if (MODO_MOCK) return simulado(() => actualizarLaboratorioMock(id, datos));
  return peticion<Laboratorio>("PUT", `/laboratorios/${encodeURIComponent(id)}`, datos);
}

export async function eliminarLaboratorio(id: IdNumerico): Promise<void> {
  if (MODO_MOCK) {
    await simulado(() => {
      estadoMock.cohortes.forEach((cohorte) => {
        cohorte.laboratorios = cohorte.laboratorios.filter((l) => l.id !== id);
      });
      return null;
    });
    return;
  }
  return peticionSinContenido("DELETE", `/laboratorios/${encodeURIComponent(id)}`);
}

// ---------- Rúbricas ----------

export async function obtenerRubricaVigente(laboratorioId: IdNumerico): Promise<RubricaVersion> {
  if (MODO_MOCK) return simulado(() => rubricaVigenteMock(laboratorioId));
  return peticion<RubricaVersion>("GET", `/laboratorios/${encodeURIComponent(laboratorioId)}/rubrica`);
}

/** Igual que obtenerRubricaVigente, pero devuelve null si el laboratorio no tiene versión vigente (404). */
export async function obtenerRubricaVigenteONula(laboratorioId: IdNumerico): Promise<RubricaVersion | null> {
  try {
    const rubrica = await obtenerRubricaVigente(laboratorioId);
    return rubrica.estado === "aprobada" ? rubrica : null;
  } catch (causa) {
    if (causa instanceof ErrorApi && causa.status === 404) return null;
    throw causa;
  }
}

export async function extraerRubrica(laboratorioId: IdNumerico, archivo: File): Promise<ResultadoExtraccion> {
  if (MODO_MOCK) {
    await esperar(1200);
    return simulado(() => {
      if (!existeLaboratorioMock(laboratorioId)) throw noEncontrado();
      const rubrica = { ...rubricaExtraidaMock, titulo: `Rúbrica extraída de ${archivo.name}` };
      return { rubrica, inconsistencias: validarRubricaMock(rubrica).inconsistencias };
    });
  }
  const formulario = new FormData();
  formulario.append("archivo", archivo);
  return peticion<ResultadoExtraccion>(
    "POST",
    `/laboratorios/${encodeURIComponent(laboratorioId)}/rubrica/extraer`,
    formulario,
  );
}

export async function validarRubrica(rubrica: Rubrica): Promise<ResultadoValidacion> {
  if (MODO_MOCK) return simulado(() => validarRubricaMock(rubrica));
  return peticion<ResultadoValidacion>("POST", "/rubricas/validar", rubrica);
}

export async function guardarVersionRubrica(laboratorioId: IdNumerico, rubrica: Rubrica): Promise<RubricaVersion> {
  if (MODO_MOCK) return simulado(() => guardarVersionMock(laboratorioId, rubrica));
  return peticion<RubricaVersion>(
    "POST",
    `/laboratorios/${encodeURIComponent(laboratorioId)}/rubrica/versiones`,
    rubrica,
  );
}

// ---------- Entregas ----------

export async function listarEntregas(estudianteId?: string): Promise<Entrega[]> {
  if (MODO_MOCK) {
    return simulado(() =>
      estudianteId ? estadoMock.entregas.filter((e) => e.estudiante_id === estudianteId) : estadoMock.entregas,
    );
  }
  const consulta = estudianteId ? `?estudiante_id=${encodeURIComponent(estudianteId)}` : "";
  return peticion<Entrega[]>("GET", `/entregas${consulta}`);
}

export async function crearEntrega(datos: NuevaEntrega): Promise<Entrega> {
  if (MODO_MOCK) {
    return simulado(() => {
      validarEntregaMock(datos);
      const entrega: Entrega = {
        id: nuevoIdMock(),
        estudiante_id: perfilesMock.estudiante.id,
        laboratorio_id: datos.laboratorio_id,
        rubrica_version_id: rubricaVigenteMock(datos.laboratorio_id).id,
        pdf_path: datos.pdf.name,
        codigo_zip_path: datos.zip?.name ?? null,
        github_url: datos.github_url ?? null,
        extras: (datos.extras ?? []).map((archivo) => archivo.name),
        creada_en: new Date().toISOString(),
        evaluacion: null,
      };
      estadoMock.entregas.push(entrega);
      return entrega;
    });
  }
  const formulario = new FormData();
  formulario.append("laboratorio_id", String(datos.laboratorio_id));
  formulario.append("pdf", datos.pdf);
  if (datos.zip) formulario.append("zip", datos.zip);
  if (datos.github_url) formulario.append("github_url", datos.github_url);
  (datos.extras ?? []).forEach((archivo) => formulario.append("extras", archivo));
  return peticion<Entrega>("POST", "/entregas", formulario);
}

export async function evaluarEntrega(entregaId: IdNumerico): Promise<RespuestaEvaluar> {
  if (MODO_MOCK) {
    const perfil = await perfilMockActual();
    return simulado(() => {
      const entrega = estadoMock.entregas.find((e) => e.id === entregaId);
      if (!entrega) throw noEncontrado();
      if (entrega.evaluacion && entrega.evaluacion.estado !== "error") {
        throw new ErrorApi(409, "Esta entrega ya fue enviada a evaluación.");
      }
      const evaluacion = crearEvaluacionEnProcesoMock(entrega, perfil);
      entrega.evaluacion = { id: evaluacion.id, estado: evaluacion.estado, nota: null };
      const respuesta: RespuestaEvaluar = { evaluacion_id: evaluacion.id, estado: evaluacion.estado };
      return respuesta;
    });
  }
  return peticion<RespuestaEvaluar>("POST", `/entregas/${encodeURIComponent(entregaId)}/evaluar`);
}

// ---------- Evaluaciones ----------

/** Tamaño de página por defecto del listado docente (el backend acepta limit 1–LIMIT_MAXIMO). */
export const LIMITE_EVALUACIONES_POR_DEFECTO = 20;

export async function obtenerEvaluacion(id: IdNumerico): Promise<Evaluacion> {
  if (MODO_MOCK) {
    const perfil = await perfilMockActual();
    return simulado(() => {
      const evaluacion = buscarEvaluacionMock(id);
      if (perfil.rol !== "estudiante") return evaluacion;
      verificarAccesoEstudianteMock(evaluacion, perfil.id);
      return vistaEstudianteMock(evaluacion);
    });
  }
  return peticion<Evaluacion>("GET", `/evaluaciones/${id}`);
}

/** GET /evaluaciones (docente): filtros + paginación con limit/offset. */
export async function listarEvaluaciones(filtros: FiltrosEvaluaciones = {}): Promise<ListadoEvaluaciones> {
  if (MODO_MOCK) {
    await exigirRolMock(ROLES_GESTION_MOCK);
    return simulado(() => listarEvaluacionesMock(filtros));
  }
  const consulta = new URLSearchParams();
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== "") consulta.set(clave, String(valor));
  });
  const texto = consulta.toString();
  return peticion<ListadoEvaluaciones>("GET", `/evaluaciones${texto ? `?${texto}` : ""}`);
}

export async function ajustarCriterio(
  evaluacionId: IdNumerico,
  criterioId: string,
  ajuste: AjusteCriterio,
): Promise<Evaluacion> {
  if (MODO_MOCK) {
    const perfil = await perfilMockActual();
    return simulado(() => ajustarCriterioMock(evaluacionId, criterioId, ajuste, perfil));
  }
  return peticion<Evaluacion>("PATCH", `/evaluaciones/${evaluacionId}/criterios/${encodeURIComponent(criterioId)}`, ajuste);
}

/** PATCH /evaluaciones/{id}/retroalimentacion: textos generales y/o por criterio (motivo opcional). */
export async function editarRetroalimentacion(id: IdNumerico, entrada: RetroalimentacionEntrada): Promise<Evaluacion> {
  if (MODO_MOCK) {
    const perfil = await perfilMockActual();
    return simulado(() => editarRetroalimentacionMock(id, entrada, perfil));
  }
  return peticion<Evaluacion>("PATCH", `/evaluaciones/${id}/retroalimentacion`, entrada);
}

/** POST /evaluaciones/{id}/revisar: borrador → en_revision. */
export async function pasarARevision(id: IdNumerico): Promise<Evaluacion> {
  if (MODO_MOCK) {
    const perfil = await perfilMockActual();
    return simulado(() => cambiarEstadoMock(id, "revisar", perfil));
  }
  return peticion<Evaluacion>("POST", `/evaluaciones/${id}/revisar`);
}

/** POST /evaluaciones/{id}/aprobar: en_revision → aprobada. */
export async function aprobarEvaluacion(id: IdNumerico): Promise<Evaluacion> {
  if (MODO_MOCK) {
    const perfil = await perfilMockActual();
    return simulado(() => cambiarEstadoMock(id, "aprobar", perfil));
  }
  return peticion<Evaluacion>("POST", `/evaluaciones/${id}/aprobar`);
}

/** POST /evaluaciones/{id}/publicar: aprobada → publicada. */
export async function publicarEvaluacion(id: IdNumerico): Promise<Evaluacion> {
  if (MODO_MOCK) {
    const perfil = await perfilMockActual();
    return simulado(() => cambiarEstadoMock(id, "publicar", perfil));
  }
  return peticion<Evaluacion>("POST", `/evaluaciones/${id}/publicar`);
}

/** Máximo de `limit` que aceptan los listados paginados del backend. */
export const LIMITE_MAXIMO_LISTADO = 100;

/** GET /estudiantes (docente): estudiantes por nombre con sus laboratorios evaluados (paginado). */
export async function listarEstudiantes(limit = LIMITE_MAXIMO_LISTADO, offset = 0): Promise<ListadoEstudiantes> {
  if (MODO_MOCK) {
    await exigirRolMock(ROLES_GESTION_MOCK);
    return simulado(() => listarEstudiantesMock(limit, offset));
  }
  return peticion<ListadoEstudiantes>("GET", `/estudiantes?limit=${limit}&offset=${offset}`);
}

export async function obtenerTraza(id: IdNumerico): Promise<Traza> {
  if (MODO_MOCK) return simulado(() => trazaDeEvaluacionMock(buscarEvaluacionMock(id)));
  return peticion<Traza>("GET", `/evaluaciones/${id}/traza`);
}

// ---------- Informe y mapa ----------
// La primera consulta puede tardar hasta ~60 s porque el backend genera la narrativa y el mapeo con IA en la
// misma petición. Por eso solo estas dos peticiones usan TIEMPO_ESPERA_GENERACION_MS.

const informesMock: Record<string, Informe> = {
  [informeMock.estudiante.id]: informeMock,
  [informeSinPublicadasMock.estudiante.id]: informeSinPublicadasMock,
  [informeNarrativaErrorMock.estudiante.id]: informeNarrativaErrorMock,
};

const mapasMock: Record<string, Mapa> = {
  [informeMock.estudiante.id]: mapaMock,
  [informeSinPublicadasMock.estudiante.id]: mapaVacioMock,
  [informeNarrativaErrorMock.estudiante.id]: mapaConAvisosMock,
};

/** Demora simulada de la primera generación (después queda "en caché", como en el backend). */
const DEMORA_GENERACION_MOCK_MS = 6000;
const generadosMock = new Set<string>();

/** Simula la generación con IA respetando el mismo límite de espera que la petición real. */
async function generarMock<T>(clave: string, producir: () => T): Promise<T> {
  const demora = generadosMock.has(clave) ? 300 : DEMORA_GENERACION_MOCK_MS;
  if (demora >= TIEMPO_ESPERA_GENERACION_MS) {
    await esperar(TIEMPO_ESPERA_GENERACION_MS);
    throw new ErrorApi(408, MENSAJE_TIEMPO_AGOTADO);
  }
  await esperar(demora);
  generadosMock.add(clave);
  return structuredClone(producir());
}

/** Simula el permiso del backend: el estudiante solo ve lo suyo (si pide otro, 404); docente y admin, cualquiera. */
async function exigirAccesoEstudianteMock(estudianteId: string): Promise<void> {
  const perfil = await perfilMockActual();
  if (perfil.rol === "estudiante" && perfil.id !== estudianteId) throw noEncontrado();
}

/** Estudiante del mock (404 si no existe, como el backend). */
function estudianteMock(estudianteId: string): Usuario {
  const estudiante = estadoMock.usuarios.find((u) => u.id === estudianteId && u.rol === "estudiante");
  if (!estudiante) throw new ErrorApi(404, "No encontramos un estudiante con ese identificador.");
  return estudiante;
}

/** Estudiante sin evaluaciones publicadas: el backend responde números vacíos y narrativa "sin_datos". */
function informeSinDatosMock(estudianteId: string): Informe {
  const { id, nombre } = estudianteMock(estudianteId);
  return { ...informeSinPublicadasMock, estudiante: { id, nombre } };
}

export async function obtenerInforme(estudianteId: string): Promise<Informe> {
  if (MODO_MOCK) {
    await exigirAccesoEstudianteMock(estudianteId);
    const informe = informesMock[estudianteId] ?? informeSinDatosMock(estudianteId);
    return generarMock(`informe:${estudianteId}`, () => informe);
  }
  return peticion<Informe>("GET", `/estudiantes/${encodeURIComponent(estudianteId)}/informe`, undefined, LIMITE_GENERACION);
}

export async function obtenerMapa(estudianteId: string): Promise<Mapa> {
  if (MODO_MOCK) {
    await exigirAccesoEstudianteMock(estudianteId);
    const mapa = mapasMock[estudianteId] ?? (estudianteMock(estudianteId) && mapaVacioMock);
    return generarMock(`mapa:${estudianteId}`, () => mapa);
  }
  return peticion<Mapa>("GET", `/estudiantes/${encodeURIComponent(estudianteId)}/mapa`, undefined, LIMITE_GENERACION);
}

// ---------- Configuración de IA ----------

/** GET /config-ia (solo admin). */
export async function obtenerConfigIA(): Promise<ConfigIA> {
  if (MODO_MOCK) {
    await exigirRolMock(ROLES_CONFIG_IA_MOCK);
    return simulado(() => estadoMock.config);
  }
  return peticion<ConfigIA>("GET", "/config-ia");
}

/** PUT /config-ia (solo admin): siempre {proveedor, modelo, temperatura}. Si no cambia nada responde 200 igual. */
export async function guardarConfigIA(datos: ConfigIAEntrada): Promise<ConfigIA> {
  const cuerpo: ConfigIAEntrada = { proveedor: datos.proveedor, modelo: datos.modelo, temperatura: datos.temperatura };
  if (MODO_MOCK) {
    const perfil = await exigirRolMock(ROLES_CONFIG_IA_MOCK);
    return simulado(() => guardarConfigMock(cuerpo, perfil));
  }
  return peticion<ConfigIA>("PUT", "/config-ia", cuerpo);
}

/** Límite de espera de "Probar conexión" (el backend corta a los ~10 s). */
export const TIEMPO_ESPERA_PRUEBA_MS = 15_000;

const MENSAJE_PRUEBA_AGOTADA =
  "La prueba de conexión tardó más de 15 segundos y se canceló. Revisa el proveedor e intenta de nuevo.";

/** POST /config-ia/probar (solo admin): sin cuerpo; prueba la configuración guardada y responde siempre 200. */
export async function probarConfigIA(): Promise<ResultadoPruebaIA> {
  if (MODO_MOCK) {
    await exigirRolMock(ROLES_CONFIG_IA_MOCK);
    await esperar(DEMORA_PRUEBA_MOCK_MS);
    return simulado(probarConfigMock);
  }
  return peticion<ResultadoPruebaIA>("POST", "/config-ia/probar", undefined, {
    ms: TIEMPO_ESPERA_PRUEBA_MS,
    mensaje: MENSAJE_PRUEBA_AGOTADA,
  });
}
