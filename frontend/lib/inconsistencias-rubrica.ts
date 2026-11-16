// Detección de inconsistencias de una rúbrica (RF-03 CA2 y §7). Lógica pura, sin React.
// La usan el editor (validación en vivo) y el modo mock del API. La validación oficial la hace el backend.
// Decisión: los puntajes de los niveles deben ir en orden descendente (del mejor nivel al peor).
import type { CriterioRubrica, Inconsistencia, NivelDesempeno, Rubrica, TipoInconsistencia } from "@/lib/tipos";

/** Nivel en edición: el puntaje puede estar vacío mientras se escribe. */
export type NivelBorrador = Omit<NivelDesempeno, "puntaje"> & { puntaje: number | null };

/** Criterio en edición: la ponderación puede estar vacía mientras se escribe. */
export type CriterioBorrador = Omit<CriterioRubrica, "ponderacion" | "niveles"> & {
  ponderacion: number | null;
  niveles: NivelBorrador[];
};

export interface RubricaBorrador {
  titulo: string;
  criterios: CriterioBorrador[];
}

export interface InconsistenciasAgrupadas {
  /** Problemas de toda la rúbrica (p. ej. la suma de ponderaciones). */
  generales: Inconsistencia[];
  /** Problemas de cada criterio, en el mismo orden de `rubrica.criterios`. */
  porCriterio: Inconsistencia[][];
}

const TOLERANCIA_SUMA = 0.01;

const formato = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

export function formatearNumero(valor: number): string {
  return formato.format(valor);
}

function normalizar(texto: string): string {
  return texto.trim().toLocaleLowerCase("es");
}

function esNumero(valor: number | null): valor is number {
  return valor !== null && Number.isFinite(valor);
}

/** Suma de ponderaciones; las vacías cuentan como 0. */
export function sumaPonderaciones(rubrica: RubricaBorrador): number {
  return rubrica.criterios.reduce((total, c) => total + (esNumero(c.ponderacion) ? c.ponderacion : 0), 0);
}

export function sumaEsCorrecta(suma: number): boolean {
  return Math.abs(suma - 100) <= TOLERANCIA_SUMA;
}

function etiquetaCriterio(criterio: CriterioBorrador, indice: number): string {
  const nombre = criterio.nombre.trim();
  return nombre === "" ? `#${indice + 1}` : `"${nombre}"`;
}

function crear(tipo: TipoInconsistencia, mensaje: string, criterio: CriterioBorrador | null): Inconsistencia {
  const id = criterio?.id.trim() ?? "";
  return { tipo, mensaje, criterio_id: id === "" ? null : id };
}

/** Devuelve los valores que aparecen más de una vez (ya normalizados). */
function repetidos<T>(valores: T[]): Set<T> {
  const vistos = new Set<T>();
  const duplicados = new Set<T>();
  valores.forEach((valor) => (vistos.has(valor) ? duplicados.add(valor) : vistos.add(valor)));
  return duplicados;
}

function revisarCantidadNiveles(criterio: CriterioBorrador, etiqueta: string): Inconsistencia[] {
  if (criterio.niveles.length === 0) {
    return [crear("criterio_sin_niveles", `El criterio ${etiqueta} no tiene niveles de desempeño.`, criterio)];
  }
  if (criterio.niveles.length < 2) {
    return [crear("niveles_insuficientes", `El criterio ${etiqueta} debe tener al menos 2 niveles.`, criterio)];
  }
  return [];
}

function revisarCamposNiveles(criterio: CriterioBorrador, etiqueta: string): Inconsistencia[] {
  return criterio.niveles.flatMap((nivel, i) => {
    const nombre = nivel.nombre.trim() === "" ? `#${i + 1}` : `"${nivel.nombre.trim()}"`;
    const lista: Inconsistencia[] = [];
    if (!esNumero(nivel.puntaje)) {
      lista.push(crear("nivel_sin_puntaje", `El nivel ${nombre} del criterio ${etiqueta} no tiene puntaje.`, criterio));
    }
    if (nivel.descriptor.trim() === "") {
      lista.push(
        crear("nivel_sin_descriptor", `El nivel ${nombre} del criterio ${etiqueta} no tiene descriptor.`, criterio),
      );
    }
    return lista;
  });
}

function revisarRepetidosNiveles(criterio: CriterioBorrador, etiqueta: string): Inconsistencia[] {
  const lista: Inconsistencia[] = [];
  const nombres = repetidos(criterio.niveles.map((n) => normalizar(n.nombre)).filter((n) => n !== ""));
  if (nombres.size > 0) {
    lista.push(crear("nivel_duplicado", `El criterio ${etiqueta} tiene niveles con el mismo nombre.`, criterio));
  }
  const puntajes = repetidos(criterio.niveles.map((n) => n.puntaje).filter(esNumero));
  if (puntajes.size > 0) {
    const valores = [...puntajes].map(formatearNumero).join(", ");
    lista.push(crear("nivel_duplicado", `El criterio ${etiqueta} repite puntajes entre niveles (${valores}).`, criterio));
  }
  return lista;
}

function revisarOrdenPuntajes(criterio: CriterioBorrador, etiqueta: string): Inconsistencia[] {
  const puntajes = criterio.niveles.map((n) => n.puntaje).filter(esNumero);
  const desordenado = puntajes.some((puntaje, i) => i > 0 && puntaje > puntajes[i - 1]);
  if (!desordenado) return [];
  const mensaje = `Los puntajes del criterio ${etiqueta} deben ir de mayor a menor (del mejor nivel al peor).`;
  return [crear("puntajes_no_ordenados", mensaje, criterio)];
}

function revisarCriterio(criterio: CriterioBorrador, indice: number): Inconsistencia[] {
  const etiqueta = etiquetaCriterio(criterio, indice);
  const lista: Inconsistencia[] = [];
  if (criterio.competencia.trim() === "") {
    lista.push(crear("competencia_vacia", `El criterio ${etiqueta} no tiene competencia.`, criterio));
  }
  if (!esNumero(criterio.ponderacion) || criterio.ponderacion <= 0) {
    const mensaje = `El criterio ${etiqueta} necesita una ponderación mayor que 0 %.`;
    lista.push(crear("ponderaciones_no_suman_100", mensaje, criterio));
  }
  return [
    ...lista,
    ...revisarCantidadNiveles(criterio, etiqueta),
    ...revisarCamposNiveles(criterio, etiqueta),
    ...revisarRepetidosNiveles(criterio, etiqueta),
    ...revisarOrdenPuntajes(criterio, etiqueta),
  ];
}

/** Marca como duplicado cada criterio cuyo id o nombre ya apareció antes en la lista. */
function revisarDuplicados(criterios: CriterioBorrador[]): Inconsistencia[][] {
  const ids = new Set<string>();
  const nombres = new Set<string>();
  return criterios.map((criterio, indice) => {
    const id = normalizar(criterio.id);
    const nombre = normalizar(criterio.nombre);
    const lista: Inconsistencia[] = [];
    if (id !== "" && ids.has(id)) {
      lista.push(crear("criterio_duplicado", `El id "${criterio.id.trim()}" está repetido en otro criterio.`, criterio));
    }
    if (nombre !== "" && nombres.has(nombre)) {
      const mensaje = `El criterio ${etiquetaCriterio(criterio, indice)} está repetido (mismo nombre).`;
      lista.push(crear("criterio_duplicado", mensaje, criterio));
    }
    if (id !== "") ids.add(id);
    if (nombre !== "") nombres.add(nombre);
    return lista;
  });
}

function revisarGenerales(rubrica: RubricaBorrador): Inconsistencia[] {
  const suma = sumaPonderaciones(rubrica);
  if (sumaEsCorrecta(suma)) return [];
  const mensaje = `Las ponderaciones suman ${formatearNumero(suma)} % y deben sumar 100 %.`;
  return [crear("ponderaciones_no_suman_100", mensaje, null)];
}

/** Inconsistencias separadas en generales y por criterio (para mostrarlas junto a cada criterio). */
export function agruparInconsistencias(rubrica: RubricaBorrador): InconsistenciasAgrupadas {
  const duplicados = revisarDuplicados(rubrica.criterios);
  return {
    generales: revisarGenerales(rubrica),
    porCriterio: rubrica.criterios.map((criterio, i) => [...revisarCriterio(criterio, i), ...duplicados[i]]),
  };
}

/** Lista plana de inconsistencias con la forma del contrato (`Inconsistencia`). */
export function calcularInconsistencias(rubrica: RubricaBorrador | Rubrica): Inconsistencia[] {
  const { generales, porCriterio } = agruparInconsistencias(rubrica);
  return [...generales, ...porCriterio.flat()];
}

/**
 * Campos obligatorios vacíos que el contrato no clasifica como inconsistencia
 * (título, id y nombre del criterio, nombre del nivel). También bloquean el guardado.
 */
export function camposObligatoriosVacios(rubrica: RubricaBorrador): string[] {
  const faltantes: string[] = [];
  if (rubrica.titulo.trim() === "") faltantes.push("La rúbrica necesita un título.");
  rubrica.criterios.forEach((criterio, i) => {
    if (criterio.id.trim() === "") faltantes.push(`El criterio #${i + 1} necesita un id.`);
    if (criterio.nombre.trim() === "") faltantes.push(`El criterio #${i + 1} necesita un nombre.`);
    if (criterio.niveles.some((n) => n.nombre.trim() === "")) {
      faltantes.push(`El criterio ${etiquetaCriterio(criterio, i)} tiene niveles sin nombre.`);
    }
  });
  if (rubrica.criterios.length === 0) faltantes.push("La rúbrica necesita al menos un criterio.");
  return faltantes;
}
