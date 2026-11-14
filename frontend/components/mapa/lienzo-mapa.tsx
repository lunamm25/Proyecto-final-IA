"use client";

import "@xyflow/react/dist/style.css";
import { useEffect, type RefObject } from "react";
import { Background, Controls, MiniMap, ReactFlow, useReactFlow, type Edge, type NodeMouseHandler, type OnNodesChange } from "@xyflow/react";
import { ESTILO_NIVEL } from "@/components/mapa/estilos-mapa";
import type { NodoFlujo } from "@/components/mapa/flujo-mapa";
import { TIPOS_NODO } from "@/components/mapa/nodo-mapa";

const ETIQUETAS_ARIA = {
  "node.a11yDescription.default": "Pulsa Enter o Espacio para ver el detalle del nodo.",
  "node.a11yDescription.keyboardDisabled": "Pulsa Enter o Espacio para ver el detalle del nodo.",
  "edge.a11yDescription.default": "Relación entre dos nodos del mapa.",
  "controls.ariaLabel": "Controles del mapa",
  "controls.zoomIn.ariaLabel": "Acercar",
  "controls.zoomOut.ariaLabel": "Alejar",
  "controls.fitView.ariaLabel": "Encuadrar todo el mapa",
  "controls.interactive.ariaLabel": "Bloquear o desbloquear el arrastre",
  "minimap.ariaLabel": "Minimapa",
  "handle.ariaLabel": "Conector",
};

interface PropsLienzo {
  nodos: NodoFlujo[];
  aristas: Edge[];
  alCambiarNodos: OnNodesChange<NodoFlujo>;
  alAbrir: (id: string) => void;
  /** Cambia cada vez que se pide encuadrar (p. ej. tras expandir o colapsar todo). */
  encuadre: number;
  descripcion: string;
  contenedorRef: RefObject<HTMLDivElement | null>;
}

function colorMiniMapa(nodo: NodoFlujo): string {
  return ESTILO_NIVEL[nodo.data.nodo.nivel].colorMini;
}

/** Lienzo de React Flow: zoom, desplazamiento, arrastre de nodos, controles y minimapa (oculto en móvil). */
export function LienzoMapa({ nodos, aristas, alCambiarNodos, alAbrir, encuadre, descripcion, contenedorRef }: PropsLienzo) {
  const { fitView } = useReactFlow();
  const alHacerClic: NodeMouseHandler<NodoFlujo> = (_evento, nodo) => alAbrir(nodo.id);

  useEffect(() => {
    if (encuadre > 0) void fitView({ duration: 300, padding: 0.15 });
  }, [encuadre, fitView]);

  return (
    <div
      ref={contenedorRef}
      role="region"
      aria-label={descripcion}
      className="h-[65svh] min-h-96 w-full overflow-hidden rounded-xl border bg-card lg:h-[calc(100svh-15rem)] lg:min-h-[520px]"
    >
      <ReactFlow<NodoFlujo, Edge>
        nodes={nodos}
        edges={aristas}
        nodeTypes={TIPOS_NODO}
        onNodesChange={alCambiarNodos}
        onNodeClick={alHacerClic}
        nodesConnectable={false}
        elementsSelectable={false}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.1}
        maxZoom={2}
        ariaLabelConfig={ETIQUETAS_ARIA}
        panActivationKeyCode={null}
        deleteKeyCode={null}
      >
        <Background gap={24} />
        <Controls showInteractive={false} />
        <MiniMap<NodoFlujo> pannable zoomable nodeColor={colorMiniMapa} nodeStrokeWidth={2} className="max-md:hidden!" />
      </ReactFlow>
    </div>
  );
}
