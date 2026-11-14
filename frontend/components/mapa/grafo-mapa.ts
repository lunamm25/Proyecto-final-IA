// Funciones puras del mapa mental (RF-09): jerarquía, layout, filtros y nombres de archivo.
// Solo transforman para presentar: no crean nodos, niveles, evidencias ni relaciones.
import type { AristaMapa, Mapa, NivelDominio, NodoMapa, TipoNodo } from "@/lib/tipos";

/** Nivel para presentar: el backend envía `nivel_dominio` null cuando no hay datos; aquí se llama "sin_dato". */
export type NivelMapa = NivelDominio | "sin_dato";

export function nivelDe(nodo: Pick<NodoMapa, "nivel_dominio">): NivelMapa {
  return nodo.nivel_dominio ?? "sin_dato";
}

/** Clave estable de una arista (el backend no les da id). */
export function claveArista(arista: AristaMapa): string {
  return `${arista.origen}->${arista.destino}`;
}

export interface Jerarquia {
  /** Nodos en el orden recibido (sin ids repetidos). */
  nodos: NodoMapa[];
  porId: Map<string, NodoMapa>;
  /** Hijos por id: el primer origen de una arista que llega a un nodo es su padre (no hay padre_id). */
  hijos: Map<string, string[]>;
  padreDe: Map<string, string>;
  raices: string[];
  /** Aristas cuyo origen y destino existen; sin repetidas ni bucles. */
  aristas: AristaMapa[];
}

export interface Posicion {
  x: number;
  y: number;
}

export interface Filtro {
  consulta: string;
  niveles: ReadonlySet<NivelMapa>;
}

export const NIVELES: NivelMapa[] = ["alto", "medio", "bajo", "sin_dato"];

/** Ancho fijo por tipo de nodo (px): permite un layout estable y centrar sin medir el DOM. */
export const ANCHO_NODO: Record<TipoNodo, number> = {
  tematica: 240,
  subtema: 220,
  competencia: 210,
  concepto: 210,
  laboratorio: 200,
};
export const ALTO_APROXIMADO_NODO = 64;

const SEPARACION_COLUMNAS = 300;
const ALTO_FILA = 92;
const SEPARACION_RAICES = 36;

function nodosUnicos(nodos: NodoMapa[]): Map<string, NodoMapa> {
  const porId = new Map<string, NodoMapa>();
  nodos.forEach((nodo) => {
    if (!porId.has(nodo.id)) porId.set(nodo.id, nodo);
  });
  return porId;
}

function aristasValidas(aristas: AristaMapa[], porId: Map<string, NodoMapa>): AristaMapa[] {
  const vistas = new Set<string>();
  return aristas.filter((arista) => {
    const clave = claveArista(arista);
    const valida =
      porId.has(arista.origen) && porId.has(arista.destino) && arista.origen !== arista.destino && !vistas.has(clave);
    vistas.add(clave);
    return valida;
  });
}

function agregarHijo(hijos: Map<string, string[]>, padre: string, hijo: string): void {
  hijos.set(padre, [...(hijos.get(padre) ?? []), hijo]);
}

/** Recorre desde `id` marcando visitados (sirve para detectar ciclos en las aristas). */
function marcarAlcanzables(id: string, hijos: Map<string, string[]>, visitados: Set<string>): void {
  const pila = [id];
  while (pila.length > 0) {
    const actual = pila.pop() as string;
    if (visitados.has(actual)) continue;
    visitados.add(actual);
    pila.push(...(hijos.get(actual) ?? []));
  }
}

/** Rompe ciclos: el primer nodo inalcanzable de cada ciclo pasa a ser raíz. */
function romperCiclos(j: Jerarquia): void {
  const visitados = new Set<string>();
  j.raices.forEach((raiz) => marcarAlcanzables(raiz, j.hijos, visitados));
  j.nodos.forEach((nodo) => {
    if (visitados.has(nodo.id)) return;
    const padre = j.padreDe.get(nodo.id);
    if (padre) j.hijos.set(padre, (j.hijos.get(padre) ?? []).filter((h) => h !== nodo.id));
    j.padreDe.delete(nodo.id);
    j.raices.push(nodo.id);
    marcarAlcanzables(nodo.id, j.hijos, visitados);
  });
}

/**
 * Organiza los nodos del backend en árbol a partir de las aristas (en el orden recibido): la primera arista que
 * llega a un nodo define su padre; las demás son relaciones transversales. Ignora aristas inválidas.
 */
export function construirJerarquia(mapa: Mapa): Jerarquia {
  const porId = nodosUnicos(mapa.nodos);
  const j: Jerarquia = {
    nodos: [...porId.values()],
    porId,
    hijos: new Map(),
    padreDe: new Map(),
    raices: [],
    aristas: aristasValidas(mapa.aristas, porId),
  };
  j.aristas.forEach(({ origen, destino }) => {
    if (j.padreDe.has(destino)) return;
    j.padreDe.set(destino, origen);
    agregarHijo(j.hijos, origen, destino);
  });
  j.nodos.forEach((nodo) => {
    if (!j.padreDe.has(nodo.id)) j.raices.push(nodo.id);
  });
  romperCiclos(j);
  return j;
}

/** Ids en orden de recorrido en profundidad (el mismo orden de la vista de lista). */
export function ordenProfundidad(j: Jerarquia): string[] {
  const orden: string[] = [];
  const visitar = (id: string) => {
    orden.push(id);
    (j.hijos.get(id) ?? []).forEach(visitar);
  };
  j.raices.forEach(visitar);
  return orden;
}

/**
 * Layout de árbol horizontal y determinista: columna = profundidad, las hojas se apilan
 * y cada padre queda centrado frente a sus hijos. Devuelve la esquina superior izquierda.
 */
export function calcularPosiciones(j: Jerarquia): Map<string, Posicion> {
  const posiciones = new Map<string, Posicion>();
  let cursor = 0;
  const ubicar = (id: string, profundidad: number): number => {
    const hijos = j.hijos.get(id) ?? [];
    let centro: number;
    if (hijos.length === 0) {
      centro = cursor;
      cursor += ALTO_FILA;
    } else {
      const centros = hijos.map((hijo) => ubicar(hijo, profundidad + 1));
      centro = (centros[0] + centros[centros.length - 1]) / 2;
    }
    posiciones.set(id, { x: profundidad * SEPARACION_COLUMNAS, y: centro - ALTO_APROXIMADO_NODO / 2 });
    return centro;
  };
  j.raices.forEach((raiz) => {
    ubicar(raiz, 0);
    cursor += SEPARACION_RAICES;
  });
  return posiciones;
}

export function descendientes(j: Jerarquia, id: string): string[] {
  const visitados = new Set<string>();
  marcarAlcanzables(id, j.hijos, visitados);
  visitados.delete(id);
  return [...visitados];
}

export function ancestros(j: Jerarquia, id: string): string[] {
  const lista: string[] = [];
  let actual = j.padreDe.get(id);
  while (actual !== undefined && !lista.includes(actual)) {
    lista.push(actual);
    actual = j.padreDe.get(actual);
  }
  return lista;
}

/** Nodos ocultos porque algún ancestro está colapsado. */
export function idsOcultos(j: Jerarquia, colapsados: ReadonlySet<string>): Set<string> {
  const ocultos = new Set<string>();
  colapsados.forEach((id) => descendientes(j, id).forEach((d) => ocultos.add(d)));
  return ocultos;
}

export function idsConHijos(j: Jerarquia): string[] {
  return [...j.hijos.entries()].filter(([, hijos]) => hijos.length > 0).map(([id]) => id);
}

export function normalizarTexto(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

export function filtroActivo(filtro: Filtro): boolean {
  return normalizarTexto(filtro.consulta) !== "" || filtro.niveles.size < NIVELES.length;
}

export function coincide(nodo: NodoMapa, filtro: Filtro): boolean {
  const consulta = normalizarTexto(filtro.consulta);
  return filtro.niveles.has(nivelDe(nodo)) && (consulta === "" || normalizarTexto(nodo.etiqueta).includes(consulta));
}

/** Ids que cumplen búsqueda y filtro, en orden de profundidad. */
export function idsCoincidentes(j: Jerarquia, filtro: Filtro): string[] {
  return ordenProfundidad(j).filter((id) => {
    const nodo = j.porId.get(id);
    return nodo !== undefined && coincide(nodo, filtro);
  });
}

/** Para la vista de lista: coincidencias más sus ancestros (para conservar el contexto). */
export function idsVisiblesEnLista(j: Jerarquia, coincidencias: Iterable<string>): Set<string> {
  const visibles = new Set<string>();
  for (const id of coincidencias) {
    visibles.add(id);
    ancestros(j, id).forEach((a) => visibles.add(a));
  }
  return visibles;
}

/** "Ana Pérez" → "mapa-ana-perez.png". */
export function nombreArchivo(nombre: string, extension: "png" | "json"): string {
  const base = normalizarTexto(nombre).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return `mapa-${base || "estudiante"}.${extension}`;
}
