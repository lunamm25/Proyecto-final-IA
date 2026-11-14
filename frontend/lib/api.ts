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
  mapaMock,
  perfilesMock,
  rubricaVersionMock,
  trazaMock,
  usuariosMock,
} from "@/lib/mocks";
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
  Inconsistencia,
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
};

function noEncontrado(): ErrorApi {
  return new ErrorApi(404, MENSAJES_POR_ESTADO[404]);
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

/** Validación aproximada solo para el modo mock; la validación oficial la hace el backend. */
function validarRubricaMock(rubrica: Rubrica): ResultadoValidacion {
  const inconsistencias: Inconsistencia[] = [];
  const suma = rubrica.criterios.reduce((total, c) => total + c.ponderacion, 0);
  if (Math.abs(suma - 100) > 0.01) {
    inconsistencias.push({
      tipo: "ponderaciones_no_suman_100",
      mensaje: `Las ponderaciones suman ${suma} % y deben sumar 100 %.`,
      criterio_id: null,
    });
  }
  rubrica.criterios.forEach((criterio) => {
    if (criterio.competencia.trim() === "") {
      inconsistencias.push({
        tipo: "competencia_vacia",
        mensaje: `El criterio "${criterio.nombre}" no tiene competencia.`,
        criterio_id: criterio.id,
      });
    }
    if (criterio.niveles.length === 0) {
      inconsistencias.push({
        tipo: "criterio_sin_niveles",
        mensaje: `El criterio "${criterio.nombre}" no tiene niveles.`,
        criterio_id: criterio.id,
      });
    }
    criterio.niveles.forEach((nivel) => {
      if (nivel.descriptor.trim() === "") {
        inconsistencias.push({
          tipo: "nivel_sin_descriptor",
          mensaje: `El nivel "${nivel.nombre}" del criterio "${criterio.nombre}" no tiene descriptor.`,
          criterio_id: criterio.id,
        });
      }
    });
  });
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
      const cohorte = estadoMock.cohortes.find((c) => c.id === datos.cohorte_id);
      if (!cohorte) throw noEncontrado();
      const laboratorio: Laboratorio = { ...datos, id: `lab-${Date.now()}` };
      cohorte.laboratorios.push(laboratorio);
      return laboratorio;
    });
  }
  return peticion<Laboratorio>("POST", "/laboratorios", datos);
}

export async function actualizarLaboratorio(id: string, datos: LaboratorioEntrada): Promise<Laboratorio> {
  if (MODO_MOCK) {
    return simulado(() => {
      for (const cohorte of estadoMock.cohortes) {
        const indice = cohorte.laboratorios.findIndex((l) => l.id === id);
        if (indice >= 0) {
          const laboratorio: Laboratorio = { ...datos, id };
          cohorte.laboratorios[indice] = laboratorio;
          return laboratorio;
        }
      }
      throw noEncontrado();
    });
  }
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
  if (MODO_MOCK) return simulado(() => ({ ...rubricaVersionMock, laboratorio_id: laboratorioId }));
  return peticion<RubricaVersion>("GET", `/laboratorios/${encodeURIComponent(laboratorioId)}/rubrica`);
}

export async function extraerRubrica(laboratorioId: string, archivo: File): Promise<ResultadoExtraccion> {
  if (MODO_MOCK) {
    return simulado(() => {
      const rubrica = rubricaVersionMock.contenido;
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
  if (MODO_MOCK) {
    return simulado(() => {
      const validacion = validarRubricaMock(rubrica);
      if (!validacion.valida) {
        throw new ErrorApi(422, "La rúbrica tiene inconsistencias y no se puede aprobar.");
      }
      return {
        ...rubricaVersionMock,
        id: `rv-${Date.now()}`,
        laboratorio_id: laboratorioId,
        version: rubricaVersionMock.version + 1,
        contenido: rubrica,
        creada_en: new Date().toISOString(),
      };
    });
  }
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
      const entrega: Entrega = {
        id: `ent-${Date.now()}`,
        estudiante_id: perfilesMock.estudiante.id,
        laboratorio_id: datos.laboratorio_id,
        rubrica_version_id: rubricaVersionMock.id,
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
  if (MODO_MOCK) return simulado(() => ({ evaluacion_id: "eva-2", estado: "borrador" as const }));
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
