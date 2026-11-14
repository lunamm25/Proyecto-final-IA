// Edición de la retroalimentación (PATCH /evaluaciones/{id}/retroalimentacion). Funciones puras: el formulario
// trabaja con textos (las listas, una por línea) y solo se envía lo que cambió. Límites de RetroalimentacionEntrada.
import type {
  EvaluacionCriterio,
  Retroalimentacion,
  RetroalimentacionCriterioEntrada,
  RetroalimentacionEntrada,
} from "@/lib/tipos";

export const MAX_TEXTO_LARGO = 5000;
export const MAX_ELEMENTO_LISTA = 1000;
export const MAX_ELEMENTOS_LISTA = 30;
export const MAX_MOTIVO_EDICION = 1000;

export type Errores<C extends string> = Partial<Record<C | "motivo" | "general", string>>;

/** Una línea = un elemento; se ignoran las líneas vacías. */
export function aLista(texto: string): string[] {
  return texto
    .split("\n")
    .map((linea) => linea.trim())
    .filter((linea) => linea !== "");
}

export function aTexto(lista: string[]): string {
  return lista.join("\n");
}

function iguales(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((valor, i) => valor === b[i]);
}

function errorTexto(texto: string): string | undefined {
  if (texto.trim() === "") return "No puede quedar vacío: escribe un texto o deja el anterior.";
  if (texto.trim().length > MAX_TEXTO_LARGO) return `Máximo ${MAX_TEXTO_LARGO} caracteres.`;
  return undefined;
}

function errorLista(lista: string[]): string | undefined {
  if (lista.length === 0) return "Escribe al menos un elemento (uno por línea).";
  if (lista.length > MAX_ELEMENTOS_LISTA) return `Máximo ${MAX_ELEMENTOS_LISTA} elementos.`;
  if (lista.some((e) => e.length > MAX_ELEMENTO_LISTA)) return `Cada elemento admite máximo ${MAX_ELEMENTO_LISTA} caracteres.`;
  return undefined;
}

export function errorMotivo(motivo: string): string | undefined {
  return motivo.trim().length > MAX_MOTIVO_EDICION ? `Máximo ${MAX_MOTIVO_EDICION} caracteres.` : undefined;
}

// ---------- Retroalimentación general ----------

export interface FormularioGeneral {
  retroalimentacion_general: string;
  como_aplico_conocimientos: string;
  aprendizajes_identificados: string;
  aspectos_a_fortalecer: string;
}

export type CampoGeneral = keyof FormularioGeneral;

export function formularioGeneral(retro: Retroalimentacion | null): FormularioGeneral {
  return {
    retroalimentacion_general: retro?.retroalimentacion_general ?? "",
    como_aplico_conocimientos: retro?.como_aplico_conocimientos ?? "",
    aprendizajes_identificados: aTexto(retro?.aprendizajes_identificados ?? []),
    aspectos_a_fortalecer: aTexto(retro?.aspectos_a_fortalecer ?? []),
  };
}

/** Cambios respecto a lo guardado y sus errores (solo se validan los campos que cambiaron). */
export function cambiosGenerales(
  formulario: FormularioGeneral,
  actual: Retroalimentacion | null,
): { cambios: Omit<RetroalimentacionEntrada, "criterios" | "motivo">; errores: Errores<CampoGeneral> } {
  const base = formularioGeneral(actual);
  const cambios: Omit<RetroalimentacionEntrada, "criterios" | "motivo"> = {};
  const errores: Errores<CampoGeneral> = {};
  for (const campo of ["retroalimentacion_general", "como_aplico_conocimientos"] as const) {
    if (formulario[campo].trim() === base[campo].trim()) continue;
    const error = errorTexto(formulario[campo]);
    if (error) errores[campo] = error;
    else cambios[campo] = formulario[campo].trim();
  }
  for (const campo of ["aprendizajes_identificados", "aspectos_a_fortalecer"] as const) {
    const lista = aLista(formulario[campo]);
    if (iguales(lista, aLista(base[campo]))) continue;
    const error = errorLista(lista);
    if (error) errores[campo] = error;
    else cambios[campo] = lista;
  }
  return { cambios, errores };
}

// ---------- Retroalimentación de un criterio ----------

export interface FormularioCriterio {
  justificacion: string;
  fortalezas: string;
  debilidades: string;
  recomendacion: string;
}

export type CampoCriterio = keyof FormularioCriterio;

export function formularioCriterio(criterio: EvaluacionCriterio): FormularioCriterio {
  return {
    justificacion: criterio.justificacion ?? "",
    fortalezas: aTexto(criterio.fortalezas),
    debilidades: aTexto(criterio.debilidades),
    recomendacion: criterio.recomendacion ?? "",
  };
}

export function cambiosCriterio(
  formulario: FormularioCriterio,
  criterio: EvaluacionCriterio,
): { cambios: RetroalimentacionCriterioEntrada; hayCambios: boolean; errores: Errores<CampoCriterio> } {
  const base = formularioCriterio(criterio);
  const cambios: RetroalimentacionCriterioEntrada = { criterio_id: criterio.criterio_id };
  const errores: Errores<CampoCriterio> = {};
  for (const campo of ["justificacion", "recomendacion"] as const) {
    if (formulario[campo].trim() === base[campo].trim()) continue;
    const error = errorTexto(formulario[campo]);
    if (error) errores[campo] = error;
    else cambios[campo] = formulario[campo].trim();
  }
  for (const campo of ["fortalezas", "debilidades"] as const) {
    const lista = aLista(formulario[campo]);
    if (iguales(lista, aLista(base[campo]))) continue;
    const error = errorLista(lista);
    if (error) errores[campo] = error;
    else cambios[campo] = lista;
  }
  return { cambios, hayCambios: Object.keys(cambios).length > 1, errores };
}
