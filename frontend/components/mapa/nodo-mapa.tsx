"use client";

import { memo, type MouseEvent } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Minus, Plus } from "lucide-react";
import { ESTILO_NIVEL, ESTILO_TIPO } from "@/components/mapa/estilos-mapa";
import type { NodoFlujo } from "@/components/mapa/flujo-mapa";
import { nivelDe } from "@/components/mapa/grafo-mapa";
import { cn } from "@/lib/utils";

function InsigniaNivel({ nodo }: { nodo: NodoFlujo["data"]["nodo"] }) {
  const estilo = ESTILO_NIVEL[nivelDe(nodo)];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold", estilo.claseInsignia)}>
      <estilo.Icono className="size-3" aria-hidden="true" />
      {estilo.etiqueta}
    </span>
  );
}

interface PropsAlternar {
  id: string;
  etiqueta: string;
  numHijos: number;
  colapsado: boolean;
  alAlternar: (id: string) => void;
}

function BotonAlternar({ id, etiqueta, numHijos, colapsado, alAlternar }: PropsAlternar) {
  const alHacerClic = (evento: MouseEvent) => {
    evento.stopPropagation();
    alAlternar(id);
  };
  return (
    <button
      type="button"
      onClick={alHacerClic}
      aria-expanded={!colapsado}
      aria-label={`${colapsado ? "Expandir" : "Colapsar"} ${etiqueta} (${numHijos} ${numHijos === 1 ? "elemento" : "elementos"})`}
      className="nodrag nopan absolute top-1/2 -right-3.5 flex size-7 -translate-y-1/2 items-center justify-center rounded-full border-2 border-foreground/40 bg-background text-foreground shadow-sm hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
    >
      {colapsado ? <Plus className="size-4" aria-hidden="true" /> : <Minus className="size-4" aria-hidden="true" />}
    </button>
  );
}

/** Nodo del mapa: forma por tipo, color + icono + texto por nivel, botón para expandir/colapsar. */
function NodoMapaBase({ id, data }: NodeProps<NodoFlujo>) {
  const { nodo, numHijos, colapsado, atenuado, resaltado, seleccionado } = data;
  const tipo = ESTILO_TIPO[nodo.tipo];
  const nivel = ESTILO_NIVEL[nivelDe(nodo)];
  // El clic con mouse lo maneja onNodeClick (no se dispara tras arrastrar); aquí solo teclado (detail === 0).
  const alActivar = (evento: MouseEvent) => {
    if (evento.detail === 0) data.alAbrir(id);
  };
  return (
    <div
      className={cn(
        "relative w-full text-foreground shadow-sm transition-opacity",
        tipo.claseForma,
        nivel.claseNodo,
        atenuado && "opacity-25",
        resaltado && "ring-4 ring-primary/70 ring-offset-2 ring-offset-background",
        seleccionado && "outline-3 outline-offset-4 outline-foreground",
      )}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} className="pointer-events-none opacity-0" />
      <button
        type="button"
        onClick={alActivar}
        aria-label={`${nodo.etiqueta}. ${tipo.etiqueta}. Nivel ${nivel.etiqueta}. Ver detalle`}
        className="block w-full cursor-pointer rounded-md text-left focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
      >
        <span className="flex items-center gap-1 text-[11px] text-foreground/80">
          <tipo.Icono className="size-3.5 shrink-0" aria-hidden="true" />
          {tipo.etiqueta}
        </span>
        <span className={cn("mt-0.5 line-clamp-2 leading-snug", tipo.claseTexto)} title={nodo.etiqueta}>
          {nodo.etiqueta}
        </span>
        <span className="mt-1.5 block">
          <InsigniaNivel nodo={nodo} />
        </span>
      </button>
      {numHijos > 0 && (
        <BotonAlternar id={id} etiqueta={nodo.etiqueta} numHijos={numHijos} colapsado={colapsado} alAlternar={data.alAlternar} />
      )}
      <Handle type="source" position={Position.Right} isConnectable={false} className="pointer-events-none opacity-0" />
    </div>
  );
}

export const NodoMapa = memo(NodoMapaBase);
export const TIPOS_NODO = { mapa: NodoMapa };
