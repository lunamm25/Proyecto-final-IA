/** El backend puede enviar `nombre: null`: este es el texto que se muestra en su lugar. */
export const NOMBRE_DESCONOCIDO = "Sin nombre";

/** Nombre para mostrar a partir del que envía el backend (que puede ser null o vacío). */
export function nombreVisible(nombre: string | null | undefined, respaldo: string = NOMBRE_DESCONOCIDO): string {
  const limpio = nombre?.trim();
  return limpio ? limpio : respaldo;
}

/** Iniciales (máx. 2) para el avatar cuando no hay foto. */
export function iniciales(nombre: string | null | undefined): string {
  const partes = (nombre ?? "").trim().split(/\s+/).filter(Boolean);
  const letras = partes.length > 1 ? [partes[0], partes[partes.length - 1]] : partes;
  return letras.map((parte) => parte[0]?.toUpperCase() ?? "").join("") || "?";
}
