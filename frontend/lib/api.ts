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
  laboratoriosSinRubricaMock,
  mapaMock,
  perfilesMock,
  rubricaExtraidaMock,
  rubricaVersionMock,
  trazaMock,
  usuariosMock,
} from "@/lib/mocks";
import { calcularInconsistencias } from "@/lib/inconsistencias-rubrica";
import { leerSesionMock } from "@/lib/sesion-mock";
import { obtenerSupabaseNavegador } from "@/lib/supabase/cliente";
import type {
  AjusteCriterio,
  Cohorte,
  ConfigIA,
  ConfigIAEntrada,
  Entrega,
  ErrorRespuesta,
  Evaluacion,
  EstadoEvaluacion,
  Informe,
  Laboratorio,
  LaboratorioEntrada,
  Mapa,
  NuevaEntrega,
  Perfil,
  RespuestaEvaluar,
  ResultadoExtraccion,
  ResultadoPruebaIA,
  ResultadoValidacion,
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

  constructor(status: number, mensaje: string) {
    super(mensaje);
    this.name = "ErrorApi";
    this.status = status;
  }
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

function mensajePorEstado(status: number, cuerpo: unknown): string {
  if (status >= 500) return "El servidor tuvo un problema. Intenta de nuevo en unos minutos.";
  const base = MENSAJES_POR_ESTADO[status] ?? `Error inesperado del servidor (código ${status}).`;
  if (!esErrorRespuesta(cuerpo)) return base;
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

async function enviar(metodo: Metodo, ruta: string, cuerpo?: unknown): Promise<Response> {
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
    respuesta = await fetch(`${API_URL}/api${ruta}`, { method: metodo, headers: cabeceras, body });
  } catch {
    throw new ErrorApi(0, "No se pudo conectar con el servidor. Revisa tu conexión a internet.");
  }

  if (!respuesta.ok) {
    const datos: unknown = await respuesta.json().catch(() => null);
    throw new ErrorApi(respuesta.status, mensajePorEstado(respuesta.status, datos));
  }
  return respuesta;
}

async function peticion<T>(metodo: Metodo, ruta: string, cuerpo?: unknown): Promise<T> {
  const respuesta = await enviar(metodo, ruta, cuerpo);
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

const estadoMock = {
  cohortes: structuredClone(cohortesMock),
  entregas: structuredClone(entregasMock),
  evaluaciones: structuredClone(evaluacionesMock),
  usuarios: structuredClone(usuariosMock),
  config: structuredClone(configIAMock),
  rubricas: rubricasInicialesMock(),
};

/** Versión vigente por laboratorio (en memoria); los de `laboratoriosSinRubricaMock` empiezan sin rúbrica. */
function rubricasInicialesMock(): Record<string, RubricaVersion> {
  const vigentes: Record<string, RubricaVersion> = {};
  cohortesMock
    .flatMap((cohorte) => cohorte.laboratorios)
    .filter((lab) => !laboratoriosSinRubricaMock.includes(lab.id))
    .forEach((lab) => {
      vigentes[lab.id] = { ...structuredClone(rubricaVersionMock), laboratorio_id: lab.id };
    });
  return vigentes;
}

function noEncontrado(): ErrorApi {
  return new ErrorApi(404, MENSAJES_POR_ESTADO[404]);
}

function existeLaboratorioMock(id: string): boolean {
  return estadoMock.cohortes.some((cohorte) => cohorte.laboratorios.some((l) => l.id === id));
}

function rubricaVigenteMock(laboratorioId: string): RubricaVersion {
  const vigente = estadoMock.rubricas[laboratorioId];
  if (!existeLaboratorioMock(laboratorioId) || !vigente) {
    throw new ErrorApi(404, "Este laboratorio aún no tiene una rúbrica vigente.");
  }
  return vigente;
}

function guardarVersionMock(laboratorioId: string, rubrica: Rubrica): RubricaVersion {
  if (!existeLaboratorioMock(laboratorioId)) throw noEncontrado();
  if (!validarRubricaMock(rubrica).valida) {
    throw new ErrorApi(422, "La rúbrica tiene inconsistencias y no se puede aprobar.");
  }
  const anterior = estadoMock.rubricas[laboratorioId];
  const nueva: RubricaVersion = {
    id: `rv-${Date.now()}`,
    rubrica_id: anterior?.rubrica_id ?? `rub-${laboratorioId}`,
    laboratorio_id: laboratorioId,
    version: (anterior?.version ?? 0) + 1,
    contenido: structuredClone(rubrica),
    estado: "aprobada",
    creada_por: perfilesMock.docente.id,
    creada_en: new Date().toISOString(),
  };
  estadoMock.rubricas[laboratorioId] = nueva;
  return nueva;
}

function validarCodigoUnicoMock(datos: LaboratorioEntrada, idActual: string | null): void {
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

function buscarEvaluacionMock(id: string): Evaluacion {
  const evaluacion = estadoMock.evaluaciones.find((e) => e.id === id);
  if (!evaluacion) throw noEncontrado();
  return evaluacion;
}

function cambiarEstadoMock(id: string, estado: EstadoEvaluacion): Evaluacion {
  const evaluacion = buscarEvaluacionMock(id);
  evaluacion.estado = estado;
  const ahora = new Date().toISOString();
  if (estado === "aprobada") evaluacion.aprobada_en = ahora;
  if (estado === "publicada") evaluacion.publicada_en = ahora;
  return evaluacion;
}

/** Validación del modo mock con la misma lógica del editor; la validación oficial la hace el backend. */
function validarRubricaMock(rubrica: Rubrica): ResultadoValidacion {
  const inconsistencias = calcularInconsistencias(rubrica);
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

export async function listarUsuarios(): Promise<Usuario[]> {
  if (MODO_MOCK) return simulado(() => estadoMock.usuarios);
  return peticion<Usuario[]>("GET", "/usuarios");
}

export async function cambiarRol(usuarioId: string, rol: Rol): Promise<Usuario> {
  if (MODO_MOCK) {
    return simulado(() => {
      const usuario = estadoMock.usuarios.find((u) => u.id === usuarioId);
      if (!usuario) throw noEncontrado();
      usuario.rol = rol;
      return usuario;
    });
  }
  return peticion<Usuario>("PATCH", `/usuarios/${encodeURIComponent(usuarioId)}/rol`, { rol });
}

// ---------- Cohortes y laboratorios ----------

export async function listarCohortes(): Promise<Cohorte[]> {
  if (MODO_MOCK) return simulado(() => estadoMock.cohortes);
  return peticion<Cohorte[]>("GET", "/cohortes");
}

export async function crearLaboratorio(datos: LaboratorioEntrada): Promise<Laboratorio> {
  if (MODO_MOCK) {
    return simulado(() => {
      validarCodigoUnicoMock(datos, null);
      const laboratorio: Laboratorio = { ...datos, id: `lab-${Date.now()}` };
      estadoMock.cohortes.find((c) => c.id === datos.cohorte_id)?.laboratorios.push(laboratorio);
      return laboratorio;
    });
  }
  return peticion<Laboratorio>("POST", "/laboratorios", datos);
}

/** En modo mock, si cambia la cohorte el laboratorio se mueve a la nueva cohorte. */
function actualizarLaboratorioMock(id: string, datos: LaboratorioEntrada): Laboratorio {
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

export async function actualizarLaboratorio(id: string, datos: LaboratorioEntrada): Promise<Laboratorio> {
  if (MODO_MOCK) return simulado(() => actualizarLaboratorioMock(id, datos));
  return peticion<Laboratorio>("PUT", `/laboratorios/${encodeURIComponent(id)}`, datos);
}

export async function eliminarLaboratorio(id: string): Promise<void> {
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

export async function obtenerRubricaVigente(laboratorioId: string): Promise<RubricaVersion> {
  if (MODO_MOCK) return simulado(() => rubricaVigenteMock(laboratorioId));
  return peticion<RubricaVersion>("GET", `/laboratorios/${encodeURIComponent(laboratorioId)}/rubrica`);
}

/** Igual que obtenerRubricaVigente, pero devuelve null si el laboratorio no tiene versión vigente (404). */
export async function obtenerRubricaVigenteONula(laboratorioId: string): Promise<RubricaVersion | null> {
  try {
    const rubrica = await obtenerRubricaVigente(laboratorioId);
    return rubrica.estado === "aprobada" ? rubrica : null;
  } catch (causa) {
    if (causa instanceof ErrorApi && causa.status === 404) return null;
    throw causa;
  }
}

export async function extraerRubrica(laboratorioId: string, archivo: File): Promise<ResultadoExtraccion> {
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

export async function guardarVersionRubrica(laboratorioId: string, rubrica: Rubrica): Promise<RubricaVersion> {
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
        id: `ent-${Date.now()}`,
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
  formulario.append("laboratorio_id", datos.laboratorio_id);
  formulario.append("pdf", datos.pdf);
  if (datos.zip) formulario.append("zip", datos.zip);
  if (datos.github_url) formulario.append("github_url", datos.github_url);
  (datos.extras ?? []).forEach((archivo) => formulario.append("extras", archivo));
  return peticion<Entrega>("POST", "/entregas", formulario);
}

export async function evaluarEntrega(entregaId: string): Promise<RespuestaEvaluar> {
  if (MODO_MOCK) {
    return simulado(() => {
      const entrega = estadoMock.entregas.find((e) => e.id === entregaId);
      if (!entrega) throw noEncontrado();
      if (entrega.evaluacion && entrega.evaluacion.estado !== "error") {
        throw new ErrorApi(409, "Esta entrega ya fue enviada a evaluación.");
      }
      const respuesta: RespuestaEvaluar = { evaluacion_id: `eva-${Date.now()}`, estado: "borrador" };
      entrega.evaluacion = { id: respuesta.evaluacion_id, estado: respuesta.estado, nota: null };
      return respuesta;
    });
  }
  return peticion<RespuestaEvaluar>("POST", `/entregas/${encodeURIComponent(entregaId)}/evaluar`);
}

// ---------- Evaluaciones ----------

export async function obtenerEvaluacion(id: string): Promise<Evaluacion> {
  if (MODO_MOCK) return simulado(() => buscarEvaluacionMock(id));
  return peticion<Evaluacion>("GET", `/evaluaciones/${encodeURIComponent(id)}`);
}

export async function ajustarCriterio(
  evaluacionId: string,
  criterioId: string,
  ajuste: AjusteCriterio,
): Promise<Evaluacion> {
  if (MODO_MOCK) {
    return simulado(() => {
      if (ajuste.motivo.trim() === "") throw new ErrorApi(422, "El motivo del ajuste es obligatorio.");
      const evaluacion = buscarEvaluacionMock(evaluacionId);
      const criterio = evaluacion.criterios.find((c) => c.criterio_id === criterioId);
      if (!criterio) throw noEncontrado();
      criterio.nivel_final = ajuste.nivel_final;
      criterio.ajuste_docente = ajuste.motivo;
      return evaluacion;
    });
  }
  return peticion<Evaluacion>(
    "PATCH",
    `/evaluaciones/${encodeURIComponent(evaluacionId)}/criterios/${encodeURIComponent(criterioId)}`,
    ajuste,
  );
}

export async function aprobarEvaluacion(id: string): Promise<Evaluacion> {
  if (MODO_MOCK) return simulado(() => cambiarEstadoMock(id, "aprobada"));
  return peticion<Evaluacion>("POST", `/evaluaciones/${encodeURIComponent(id)}/aprobar`);
}

export async function publicarEvaluacion(id: string): Promise<Evaluacion> {
  if (MODO_MOCK) return simulado(() => cambiarEstadoMock(id, "publicada"));
  return peticion<Evaluacion>("POST", `/evaluaciones/${encodeURIComponent(id)}/publicar`);
}

export async function obtenerTraza(id: string): Promise<Traza> {
  if (MODO_MOCK) return simulado(() => ({ ...trazaMock, evaluacion_id: buscarEvaluacionMock(id).id }));
  return peticion<Traza>("GET", `/evaluaciones/${encodeURIComponent(id)}/traza`);
}

// ---------- Informe y mapa ----------

export async function obtenerInforme(estudianteId: string): Promise<Informe> {
  if (MODO_MOCK) return simulado(() => ({ ...informeMock, estudiante_id: estudianteId }));
  return peticion<Informe>("GET", `/estudiantes/${encodeURIComponent(estudianteId)}/informe`);
}

export async function obtenerMapa(estudianteId: string): Promise<Mapa> {
  if (MODO_MOCK) return simulado(() => mapaMock);
  return peticion<Mapa>("GET", `/estudiantes/${encodeURIComponent(estudianteId)}/mapa`);
}

// ---------- Configuración de IA ----------

export async function obtenerConfigIA(): Promise<ConfigIA> {
  if (MODO_MOCK) return simulado(() => estadoMock.config);
  return peticion<ConfigIA>("GET", "/config-ia");
}

export async function guardarConfigIA(datos: ConfigIAEntrada): Promise<ConfigIA> {
  if (MODO_MOCK) {
    return simulado(() => {
      estadoMock.config = { ...datos, actualizado_por: perfilesMock.docente.id, actualizado_en: new Date().toISOString() };
      return estadoMock.config;
    });
  }
  return peticion<ConfigIA>("PUT", "/config-ia", datos);
}

export async function probarConfigIA(): Promise<ResultadoPruebaIA> {
  if (MODO_MOCK) return simulado(() => ({ ok: true, mensaje: "Conexión simulada correcta (modo mock)." }));
  return peticion<ResultadoPruebaIA>("POST", "/config-ia/probar");
}
