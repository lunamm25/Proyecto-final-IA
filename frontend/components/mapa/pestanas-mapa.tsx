"use client";

import { useRef, type KeyboardEvent } from "react";
import { ListTree, Network } from "lucide-react";
import { cn } from "@/lib/utils";

export type Vista = "grafo" | "lista";

const PESTANAS: { vista: Vista; etiqueta: string; Icono: typeof Network }[] = [
  { vista: "grafo", etiqueta: "Vista de grafo", Icono: Network },
  { vista: "lista", etiqueta: "Vista de lista", Icono: ListTree },
];

/** Pestañas accesibles (flechas izquierda/derecha) para cambiar entre grafo y lista. */
export function PestanasMapa({ vista, alCambiar }: { vista: Vista; alCambiar: (vista: Vista) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const alPresionar = (evento: KeyboardEvent, indice: number) => {
    if (evento.key !== "ArrowRight" && evento.key !== "ArrowLeft") return;
    const siguiente = (indice + (evento.key === "ArrowRight" ? 1 : -1) + PESTANAS.length) % PESTANAS.length;
    alCambiar(PESTANAS[siguiente].vista);
    refs.current[siguiente]?.focus();
  };
  return (
    <div role="tablist" aria-label="Forma de ver el mapa" className="inline-flex rounded-lg border bg-muted p-1">
      {PESTANAS.map(({ vista: valor, etiqueta, Icono }, indice) => {
        const activa = vista === valor;
        return (
          <button
            key={valor}
            ref={(elemento) => {
              refs.current[indice] = elemento;
            }}
            id={`pestana-${valor}`}
            type="button"
            role="tab"
            aria-selected={activa}
            aria-controls={`panel-vista-${valor}`}
            tabIndex={activa ? 0 : -1}
            onClick={() => alCambiar(valor)}
            onKeyDown={(evento) => alPresionar(evento, indice)}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none",
              activa ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icono className="size-4" aria-hidden="true" />
            {etiqueta}
          </button>
        );
      })}
    </div>
  );
}
