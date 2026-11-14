import type { Entrega, IdNumerico } from "@/lib/tipos";

/** Estado del laboratorio tal como lo ve el estudiante (RF-04 CA4 y RF-05 CA6). */
export type EstadoLaboratorio = "sin_entregar" | "sin_evaluar" | "pendiente" | "publicada" | "error";

export const TEXTO_ESTADO: Record<EstadoLaboratorio, string> = {
  sin_entregar: "Sin entregar",
  sin_evaluar: "Sin evaluar",
  pendiente: "Pendiente de revisión docente",
  publicada: "Publicada",
  error: "Error en la evaluación",
};

export const CLASES_ESTADO: Record<EstadoLaboratorio, string> = {
  sin_entregar: "border-zinc-300 bg-zinc-100 text-zinc-700",
  sin_evaluar: "border-sky-300 bg-sky-50 text-sky-800",
  pendiente: "border-amber-300 bg-amber-50 text-amber-800",
  publicada: "border-emerald-300 bg-emerald-50 text-emerald-800",
  error: "border-red-300 bg-red-50 text-red-800",
};

/** El estudiante no ve borrador/en_revision/aprobada: todos son "pendiente de revisión docente". */
export function estadoDeLaboratorio(entrega: Entrega | undefined): EstadoLaboratorio {
  if (!entrega) return "sin_entregar";
  if (!entrega.evaluacion) return "sin_evaluar";
  if (entrega.evaluacion.estado === "publicada") return "publicada";
  if (entrega.evaluacion.estado === "error") return "error";
  return "pendiente";
}

/** Formatea la nota que envía el backend con coma decimal (3.6 → "3,6"). No la calcula. */
export function formatearNota(nota: number): string {
  return nota.toFixed(1).replace(".", ",");
}

/** Devuelve la entrega más reciente de cada laboratorio. */
export function ultimaEntregaPorLaboratorio(entregas: Entrega[]): Map<IdNumerico, Entrega> {
  const mapa = new Map<IdNumerico, Entrega>();
  for (const entrega of entregas) {
    const actual = mapa.get(entrega.laboratorio_id);
    if (!actual || entrega.creada_en > actual.creada_en) mapa.set(entrega.laboratorio_id, entrega);
  }
  return mapa;
}

export function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });
}
