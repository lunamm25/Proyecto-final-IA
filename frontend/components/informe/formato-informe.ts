import { formatearNota } from "@/components/portafolio/estado-entrega";
import type { NivelDominio, Prioridad, PromedioCohorte } from "@/lib/tipos";

// Solo formatea los valores que envía el backend (RF-08 CA2): aquí no se calcula ningún número.

const SIN_DATOS = "Sin datos";

const TEXTO_NIVEL: Record<NivelDominio, string> = {
  bajo: "Bajo",
  medio: "Medio",
  alto: "Alto",
};

/** Nivel de dominio del backend; null = aún sin datos suficientes. */
export function textoNivel(nivel: NivelDominio | null): string {
  return nivel ? TEXTO_NIVEL[nivel] : SIN_DATOS;
}

const TEXTO_PRIORIDAD: Record<Prioridad, string> = {
  alta: "Prioridad alta",
  media: "Prioridad media",
  baja: "Prioridad baja",
};

const CLASES_PRIORIDAD: Record<Prioridad, string> = {
  alta: "border-red-300 bg-red-50 text-red-800",
  media: "border-amber-300 bg-amber-50 text-amber-800",
  baja: "border-sky-300 bg-sky-50 text-sky-800",
};

function esPrioridad(valor: string): valor is Prioridad {
  return valor === "alta" || valor === "media" || valor === "baja";
}

/** El backend envía la prioridad como texto: las conocidas tienen etiqueta y color; las demás se muestran tal cual. */
export function textoPrioridad(prioridad: string): string {
  const normalizada = prioridad.trim().toLowerCase();
  return esPrioridad(normalizada) ? TEXTO_PRIORIDAD[normalizada] : `Prioridad: ${prioridad}`;
}

export function clasesPrioridad(prioridad: string): string {
  const normalizada = prioridad.trim().toLowerCase();
  return esPrioridad(normalizada) ? CLASES_PRIORIDAD[normalizada] : "border-zinc-300 bg-zinc-100 text-zinc-700";
}

/** Nota o promedio del backend (0 a 5) o "Sin datos". */
export function textoNota(nota: number | null): string {
  return nota === null ? SIN_DATOS : formatearNota(nota);
}

/** Dominio o promedio del backend en escala 0–5: 3.5 → "3,5 / 5". */
export function formatearDominio(dominio: number | null): string {
  return dominio === null ? SIN_DATOS : `${formatearNota(dominio)} / 5`;
}

/** Diferencia que envía el backend con signo: 0.6 → "+0,6". */
export function formatearDiferencia(diferencia: number): string {
  return diferencia > 0 ? `+${formatearNota(diferencia)}` : formatearNota(diferencia);
}

/** Busca el promedio de una cohorte (por número) en la lista que envía el backend. */
export function promedioDeCohorte(promedios: PromedioCohorte[], numero: number): PromedioCohorte | undefined {
  return promedios.find((p) => p.cohorte_numero === numero);
}
