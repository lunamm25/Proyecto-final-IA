"use client";

import { useCallback, useMemo, useRef, useState, type RefObject } from "react";
import { ReactFlowProvider, applyNodeChanges, useReactFlow, type OnNodesChange } from "@xyflow/react";
import { BarraMapa, type Descarga } from "@/components/mapa/barra-mapa";
import { descargarJson, descargarPng } from "@/components/mapa/exportar-mapa";
import { crearAristas, crearNodosIniciales, decorarNodos, type NodoFlujo } from "@/components/mapa/flujo-mapa";
import {
  ALTO_APROXIMADO_NODO,
  ANCHO_NODO,
  calcularPosiciones,
  construirJerarquia,
  idsVisiblesEnLista,
  nombreArchivo,
  type Jerarquia,
} from "@/components/mapa/grafo-mapa";
import { LeyendaMapa } from "@/components/mapa/leyenda-mapa";
import { LienzoMapa } from "@/components/mapa/lienzo-mapa";
import { PanelDetalle } from "@/components/mapa/panel-detalle";
import { PestanasMapa, type Vista } from "@/components/mapa/pestanas-mapa";
import { useEstadoMapa, type EstadoMapa } from "@/components/mapa/use-estado-mapa";
import { VistaLista } from "@/components/mapa/vista-lista";
import type { Mapa } from "@/lib/tipos";

interface PropsExplorador {
  mapa: Mapa;
  /** Nombre del estudiante para los archivos descargados. */
  nombre: string;
}

function textoContador(estado: EstadoMapa, total: number): string {
  if (estado.coincidencias === null) return `Mostrando los ${total} nodos del mapa.`;
  const n = estado.listaCoincidencias.length;
  if (n === 0) return "Ningún nodo coincide. Prueba otra búsqueda o marca más niveles.";
  return `${n} de ${total} nodos coinciden con la búsqueda y el filtro.`;
}

/** Abre/cierra el panel guardando el elemento que tenía el foco para devolvérselo al cerrar. */
function usePanel(estado: EstadoMapa) {
  const origenFoco = useRef<HTMLElement | null>(null);
  const { seleccionadoId, setSeleccionadoId } = estado;
  const abrir = useCallback(
    (id: string) => {
      if (seleccionadoId === null && document.activeElement instanceof HTMLElement) origenFoco.current = document.activeElement;
      setSeleccionadoId(id);
    },
    [seleccionadoId, setSeleccionadoId],
  );
  const cerrar = useCallback(() => {
    setSeleccionadoId(null);
    const origen = origenFoco.current;
    requestAnimationFrame(() => {
      if (origen?.isConnected) origen.focus();
    });
  }, [setSeleccionadoId]);
  return { abrir, cerrar };
}

function useDescargas(mapa: Mapa, nombre: string, contenedorRef: RefObject<HTMLDivElement | null>) {
  const { getNodes } = useReactFlow<NodoFlujo>();
  const [descargando, setDescargando] = useState<Descarga | null>(null);
  const [error, setError] = useState<string | null>(null);
  const descargar = useCallback(
    async (tipo: Descarga) => {
      setError(null);
      setDescargando(tipo);
      try {
        if (tipo === "json") descargarJson(mapa, nombreArchivo(nombre, "json"));
        else if (contenedorRef.current) await descargarPng(contenedorRef.current, getNodes(), nombreArchivo(nombre, "png"));
      } catch {
        setError(`No se pudo generar el archivo ${tipo.toUpperCase()}. Intenta de nuevo.`);
      } finally {
        setDescargando(null);
      }
    },
    [mapa, nombre, contenedorRef, getNodes],
  );
  return { descargar, descargando, error };
}

/** Nodos y aristas de React Flow: posiciones en estado (arrastre) + estado visual derivado. */
function useGrafo(jerarquia: Jerarquia, estado: EstadoMapa, abrir: (id: string) => void) {
  const [nodosBase, setNodosBase] = useState<NodoFlujo[]>(() => crearNodosIniciales(jerarquia, calcularPosiciones(jerarquia)));
  const alCambiarNodos = useCallback<OnNodesChange<NodoFlujo>>((cambios) => setNodosBase((previo) => applyNodeChanges(cambios, previo)), []);
  const { ocultos, colapsados, coincidencias, hayBusqueda, seleccionadoId, alternarRama } = estado;
  const nodos = useMemo(
    () => decorarNodos(nodosBase, { ocultos, colapsados, coincidencias, hayBusqueda, seleccionadoId, alAlternar: alternarRama, alAbrir: abrir }),
    [nodosBase, ocultos, colapsados, coincidencias, hayBusqueda, seleccionadoId, alternarRama, abrir],
  );
  const aristas = useMemo(() => crearAristas(jerarquia, { ocultos, coincidencias }), [jerarquia, ocultos, coincidencias]);
  return { nodos, aristas, alCambiarNodos };
}

function ContenidoExplorador({ mapa, nombre }: PropsExplorador) {
  const jerarquia = useMemo(() => construirJerarquia(mapa), [mapa]);
  const [vista, setVista] = useState<Vista>("grafo");
  const [encuadre, setEncuadre] = useState(0);
  const contenedorRef = useRef<HTMLDivElement>(null);
  const estado = useEstadoMapa(jerarquia);
  const { abrir, cerrar } = usePanel(estado);
  const { nodos, aristas, alCambiarNodos } = useGrafo(jerarquia, estado, abrir);
  const descargas = useDescargas(mapa, nombre, contenedorRef);
  const { getNode, getZoom, setCenter } = useReactFlow<NodoFlujo>();

  const buscar = (texto: string) => {
    const primero = estado.buscar(texto);
    const nodo = primero ? getNode(primero) : undefined;
    if (vista !== "grafo" || !nodo) return;
    const ancho = ANCHO_NODO[nodo.data.nodo.tipo];
    void setCenter(nodo.position.x + ancho / 2, nodo.position.y + ALTO_APROXIMADO_NODO / 2, { zoom: Math.max(getZoom(), 1), duration: 400 });
  };
  const conEncuadre = (accion: () => void) => () => {
    accion();
    setEncuadre((valor) => valor + 1);
  };

  const seleccionado = estado.seleccionadoId ? jerarquia.porId.get(estado.seleccionadoId) : undefined;
  const total = jerarquia.nodos.length;

  return (
    <div className="space-y-4">
      <BarraMapa
        consulta={estado.consulta}
        alBuscar={buscar}
        niveles={estado.niveles}
        alAlternarNivel={estado.alternarNivel}
        alExpandirTodo={conEncuadre(estado.expandirTodo)}
        alColapsarTodo={conEncuadre(estado.colapsarTodo)}
        alDescargar={(tipo) => void descargas.descargar(tipo)}
        descargando={descargas.descargando}
        pngDisponible={vista === "grafo"}
      />
      {descargas.error && (
        <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {descargas.error}
        </p>
      )}
      <LeyendaMapa />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PestanasMapa vista={vista} alCambiar={setVista} />
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {textoContador(estado, total)}
        </p>
      </div>
      <div className="flex flex-col gap-4 lg:flex-row">
        <div id={`panel-vista-${vista}`} role="tabpanel" aria-labelledby={`pestana-${vista}`} className="min-w-0 flex-1">
          {vista === "grafo" ? (
            <LienzoMapa
              nodos={nodos}
              aristas={aristas}
              alCambiarNodos={alCambiarNodos}
              alAbrir={abrir}
              encuadre={encuadre}
              contenedorRef={contenedorRef}
              descripcion={`Grafo del mapa mental con ${total} nodos: temáticas, conceptos y laboratorios coloreados por nivel de dominio. Usa la rueda o los controles para acercar, arrastra para moverte y pulsa un nodo para ver su detalle. La vista de lista ofrece la misma información.`}
            />
          ) : (
            <VistaLista
              ctx={{
                jerarquia,
                colapsados: estado.colapsados,
                visibles: estado.coincidencias ? idsVisiblesEnLista(jerarquia, estado.coincidencias) : null,
                coincidencias: estado.coincidencias,
                seleccionadoId: estado.seleccionadoId,
                alAlternar: estado.alternarRama,
                alAbrir: abrir,
              }}
            />
          )}
        </div>
        {seleccionado && <PanelDetalle nodo={seleccionado} jerarquia={jerarquia} alCerrar={cerrar} alAbrir={abrir} />}
      </div>
    </div>
  );
}

/** Explorador interactivo del mapa mental (RF-09 CA4 y CA5). Solo se monta en el cliente. */
export function ExploradorMapa(props: PropsExplorador) {
  return (
    <ReactFlowProvider>
      <ContenidoExplorador {...props} />
    </ReactFlowProvider>
  );
}
