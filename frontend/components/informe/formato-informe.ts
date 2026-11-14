import { formatearNota } from "@/components/portafolio/estado-entrega";
import type { NivelDominio, Prioridad, PromedioCohorte } from "@/lib/tipos";

// Solo formatea los valores que envía el backend (RF-08 CA2): aquí no se calcula ningún número.

export const TEXTO_NIVEL: Record<NivelDominio, string> = {
  sin_evidencia: "Sin evidencia",
  bajo: "Bajo",
  medio: "Medio",
  alto: "Alto",
};

export const TEXTO_PRIORIDAD: Record<Prioridad, string> = {
  alta: "Prioridad alta",
  media: "Prioridad media",
  baja: "Prioridad baja",
};

export const CLASES_PRIORIDAD: Record<Prioridad, string> = {
  alta: "border-red-300 bg-red-50 text-red-800",
  media: "border-amber-300 bg-amber-50 text-amber-800",
  baja: "border-sky-300 bg-sky-50 text-sky-800",
};

/** Nota del backend o "Sin datos" si aún no hay evaluaciones publicadas. */
export function textoNota(nota: number | null): string {
  return nota === null ? "Sin datos" : formatearNota(nota);
}

/** Dominio del backend (0 a 1) mostrado como porcentaje: 0.7 → "70 %". */
export function formatearDominio(dominio: number): string {
  return `${Math.round(dominio * 100)} %`;
}

/** Diferencia que envía el backend con signo: 0.6 → "+0,6". */
export function formatearDiferencia(diferencia: number): string {
  return diferencia > 0 ? `+${formatearNota(diferencia)}` : formatearNota(diferencia);
}

/** Busca el promedio de una cohorte en la lista que envía el backend. */
export function promedioDeCohorte(promedios: PromedioCohorte[], cohorte: number): number | null {
  return promedios.find((p) => p.cohorte === cohorte)?.promedio ?? null;
}
