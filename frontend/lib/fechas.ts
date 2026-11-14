// Fechas del backend: llegan en UTC (terminan en Z) y se muestran siempre en hora de Colombia,
// sin depender de la zona horaria del navegador.

export const ZONA_HORARIA = "America/Bogota";

const FORMATO_FECHA = new Intl.DateTimeFormat("es-CO", {
  timeZone: ZONA_HORARIA,
  day: "numeric",
  month: "short",
  year: "numeric",
});

const FORMATO_FECHA_HORA = new Intl.DateTimeFormat("es-CO", {
  timeZone: ZONA_HORARIA,
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** "2026-11-14T14:35:10Z" → "14 nov 2026". */
export function formatearFecha(iso: string): string {
  return FORMATO_FECHA.format(new Date(iso));
}

/** "2026-11-14T14:35:10Z" → "14 nov 2026, 09:35 a. m." (hora de Bogotá). */
export function formatearFechaHora(iso: string): string {
  return FORMATO_FECHA_HORA.format(new Date(iso));
}
