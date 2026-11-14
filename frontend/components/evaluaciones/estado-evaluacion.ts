import type { CriterioRubrica, EstadoEvaluacion, Evaluacion, Rubrica } from "@/lib/tipos";

/** RNF-04: cada cuánto se consulta el estado mientras la evaluación se procesa. */
export const INTERVALO_SONDEO_MS = 3000;

/** Fallos de red/servidor seguidos que se toleran durante el sondeo antes de mostrar el error. */
export const MAX_FALLOS_SONDEO = 3;

export const TEXTO_ESTADO_EVALUACION: Record<EstadoEvaluacion, string> = {
  procesando: "Procesando",
  borrador: "Borrador",
  en_revision: "En revisión",
  aprobada: "Aprobada",
  publicada: "Publicada",
  error: "Error",
};

export const CLASES_ESTADO_EVALUACION: Record<EstadoEvaluacion, string> = {
  procesando: "border-violet-300 bg-violet-50 text-violet-800",
  borrador: "border-zinc-300 bg-zinc-100 text-zinc-700",
  en_revision: "border-amber-300 bg-amber-50 text-amber-800",
  aprobada: "border-sky-300 bg-sky-50 text-sky-800",
  publicada: "border-emerald-300 bg-emerald-50 text-emerald-800",
  error: "border-red-300 bg-red-50 text-red-800",
};

export const ESTADOS_EVALUACION: EstadoEvaluacion[] = [
  "procesando",
  "borrador",
  "en_revision",
  "aprobada",
  "publicada",
  "error",
];

const TEXTO_FUENTE: Record<string, string> = {
  informe: "Informe",
  codigo: "Código",
  verificacion: "Verificación técnica",
  imagen: "Imagen",
};

/** Etiqueta de la fuente de una cita (el backend la envía como texto libre). */
export function textoFuente(fuente: string): string {
  return TEXTO_FUENTE[fuente] ?? fuente;
}

/** El backend marca con "procesando" la evaluación mientras corre el pipeline en segundo plano. */
export function estaProcesando(evaluacion: Pick<Evaluacion, "estado">): boolean {
  return evaluacion.estado === "procesando";
}

/** El docente solo puede ajustar niveles mientras la evaluación está en borrador o en revisión. */
export function admiteAjustes(evaluacion: Evaluacion): boolean {
  return (evaluacion.estado === "borrador" || evaluacion.estado === "en_revision") && !estaProcesando(evaluacion);
}

export function buscarCriterioRubrica(rubrica: Rubrica | null, criterioId: string): CriterioRubrica | undefined {
  return rubrica?.criterios.find((criterio) => criterio.id === criterioId);
}

/** Fecha y hora en hora de Bogotá (ver lib/fechas.ts). */
export { formatearFechaHora } from "@/lib/fechas";
