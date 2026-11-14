import type { CriterioRubrica, EstadoEvaluacion, Evaluacion, FuenteEvidencia, Rubrica } from "@/lib/tipos";

/** RNF-04: cada cuánto se consulta el estado mientras la evaluación se procesa. */
export const INTERVALO_SONDEO_MS = 3000;

/** Fallos de red/servidor seguidos que se toleran durante el sondeo antes de mostrar el error. */
export const MAX_FALLOS_SONDEO = 3;

export const TEXTO_ESTADO_EVALUACION: Record<EstadoEvaluacion, string> = {
  borrador: "Borrador",
  en_revision: "En revisión",
  aprobada: "Aprobada",
  publicada: "Publicada",
  error: "Error",
};

export const CLASES_ESTADO_EVALUACION: Record<EstadoEvaluacion, string> = {
  borrador: "border-zinc-300 bg-zinc-100 text-zinc-700",
  en_revision: "border-amber-300 bg-amber-50 text-amber-800",
  aprobada: "border-sky-300 bg-sky-50 text-sky-800",
  publicada: "border-emerald-300 bg-emerald-50 text-emerald-800",
  error: "border-red-300 bg-red-50 text-red-800",
};

export const ESTADOS_EVALUACION: EstadoEvaluacion[] = ["borrador", "en_revision", "aprobada", "publicada", "error"];

export const TEXTO_FUENTE: Record<FuenteEvidencia, string> = {
  informe: "Informe",
  codigo: "Código",
  verificacion: "Verificación técnica",
  imagen: "Imagen",
};

/**
 * El contrato (§11) no tiene un estado "en proceso". Criterio acordado en el frontend:
 * una evaluación está procesándose si está en "borrador", sin criterios, sin nota y sin error.
 */
export function estaProcesando(evaluacion: Evaluacion): boolean {
  return (
    evaluacion.estado === "borrador" &&
    evaluacion.criterios.length === 0 &&
    evaluacion.nota === null &&
    evaluacion.error === null
  );
}

/** El docente solo puede ajustar niveles mientras la evaluación está en borrador o en revisión. */
export function admiteAjustes(evaluacion: Evaluacion): boolean {
  return (evaluacion.estado === "borrador" || evaluacion.estado === "en_revision") && !estaProcesando(evaluacion);
}

export function buscarCriterioRubrica(rubrica: Rubrica | null, criterioId: string): CriterioRubrica | undefined {
  return rubrica?.criterios.find((criterio) => criterio.id === criterioId);
}

export function formatearFechaHora(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
