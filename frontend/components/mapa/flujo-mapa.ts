// Transformación pura de la jerarquía del mapa a nodos y aristas de React Flow (solo presentación).
import type { Edge, Node } from "@xyflow/react";
import { ANCHO_NODO, claveArista, type Jerarquia, type Posicion } from "@/components/mapa/grafo-mapa";
import type { NodoMapa } from "@/lib/tipos";

export type DatosNodo = {
  nodo: NodoMapa;
  numHijos: number;
  colapsado: boolean;
  atenuado: boolean;
  resaltado: boolean;
  seleccionado: boolean;
  alAlternar: (id: string) => void;
  alAbrir: (id: string) => void;
};

export type NodoFlujo = Node<DatosNodo, "mapa">;

export interface EstadoVisual {
  ocultos: ReadonlySet<string>;
  colapsados: ReadonlySet<string>;
  /** null = no hay filtro activo (nada se atenúa). */
  coincidencias: ReadonlySet<string> | null;
  hayBusqueda: boolean;
  seleccionadoId: string | null;
  alAlternar: (id: string) => void;
  alAbrir: (id: string) => void;
}

const sinAccion = () => undefined;

/** Nodos iniciales con la posición del layout; el resto del estado se aplica en `decorarNodos`. */
export function crearNodosIniciales(j: Jerarquia, posiciones: Map<string, Posicion>): NodoFlujo[] {
  return j.nodos.map((nodo) => ({
    id: nodo.id,
    type: "mapa",
    position: posiciones.get(nodo.id) ?? { x: 0, y: 0 },
    width: ANCHO_NODO[nodo.tipo],
    focusable: false,
    selectable: false,
    connectable: false,
    data: {
      nodo,
      numHijos: j.hijos.get(nodo.id)?.length ?? 0,
      colapsado: false,
      atenuado: false,
      resaltado: false,
      seleccionado: false,
      alAlternar: sinAccion,
      alAbrir: sinAccion,
    },
  }));
}

/** Aplica visibilidad (colapsar), atenuado/resaltado (búsqueda y filtro) y selección conservando la posición. */
export function decorarNodos(nodos: NodoFlujo[], estado: EstadoVisual): NodoFlujo[] {
  return nodos.map((n) => {
    const coincide = estado.coincidencias === null || estado.coincidencias.has(n.id);
    return {
      ...n,
      hidden: estado.ocultos.has(n.id),
      data: {
        ...n.data,
        colapsado: estado.colapsados.has(n.id),
        atenuado: !coincide,
        resaltado: estado.hayBusqueda && coincide,
        seleccionado: estado.seleccionadoId === n.id,
        alAlternar: estado.alAlternar,
        alAbrir: estado.alAbrir,
      },
    };
  });
}

/** Aristas del backend (ya validadas). Las que no definen el árbol (relaciones transversales) se dibujan punteadas. */
export function crearAristas(j: Jerarquia, estado: Pick<EstadoVisual, "ocultos" | "coincidencias">): Edge[] {
  const atenuado = (id: string) => estado.coincidencias !== null && !estado.coincidencias.has(id);
  return j.aristas.map((arista) => {
    const jerarquica = j.padreDe.get(arista.destino) === arista.origen;
    return {
      id: claveArista(arista),
      source: arista.origen,
      target: arista.destino,
      hidden: estado.ocultos.has(arista.origen) || estado.ocultos.has(arista.destino),
      selectable: false,
      focusable: false,
      style: {
        strokeWidth: jerarquica ? 2 : 1.5,
        strokeDasharray: jerarquica ? undefined : "6 4",
        opacity: atenuado(arista.origen) || atenuado(arista.destino) ? 0.2 : 1,
      },
    };
  });
}
