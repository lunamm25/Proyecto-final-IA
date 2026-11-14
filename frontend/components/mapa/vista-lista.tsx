"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { ESTILO_NIVEL, ESTILO_TIPO } from "@/components/mapa/estilos-mapa";
import { nivelDe, type Jerarquia } from "@/components/mapa/grafo-mapa";
import { cn } from "@/lib/utils";

export interface ContextoLista {
  jerarquia: Jerarquia;
  colapsados: ReadonlySet<string>;
  /** null = sin filtro: se muestra todo. */
  visibles: ReadonlySet<string> | null;
  coincidencias: ReadonlySet<string> | null;
  seleccionadoId: string | null;
  alAlternar: (id: string) => void;
  alAbrir: (id: string) => void;
}

function BotonRama({ id, etiqueta, abierto, alAlternar }: { id: string; etiqueta: string; abierto: boolean; alAlternar: (id: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => alAlternar(id)}
      aria-expanded={abierto}
      aria-controls={`lista-hijos-${id}`}
      aria-label={`${abierto ? "Colapsar" : "Expandir"} ${etiqueta}`}
      className="flex size-8 shrink-0 items-center justify-center rounded-md hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
    >
      {abierto ? <ChevronDown className="size-4" aria-hidden="true" /> : <ChevronRight className="size-4" aria-hidden="true" />}
    </button>
  );
}

function ItemLista({ id, ctx }: { id: string; ctx: ContextoLista }) {
  const nodo = ctx.jerarquia.porId.get(id);
  if (!nodo || (ctx.visibles && !ctx.visibles.has(id))) return null;
  const hijos = (ctx.jerarquia.hijos.get(id) ?? []).filter((h) => !ctx.visibles || ctx.visibles.has(h));
  const abierto = !ctx.colapsados.has(id);
  const coincide = !ctx.coincidencias || ctx.coincidencias.has(id);
  const tipo = ESTILO_TIPO[nodo.tipo];
  const nivel = ESTILO_NIVEL[nivelDe(nodo)];
  return (
    <li>
      <div className="flex items-start gap-1 py-0.5">
        {hijos.length > 0 ? <BotonRama id={id} etiqueta={nodo.etiqueta} abierto={abierto} alAlternar={ctx.alAlternar} /> : <span className="size-8 shrink-0" />}
        <button
          type="button"
          onClick={() => ctx.alAbrir(id)}
          aria-current={ctx.seleccionadoId === id ? "true" : undefined}
          className={cn(
            "flex min-h-8 flex-wrap items-center gap-x-2 gap-y-1 rounded-md px-2 py-1 text-left text-sm hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none",
            ctx.seleccionadoId === id && "bg-muted",
            !coincide && "text-muted-foreground",
          )}
        >
          <tipo.Icono className="size-4 shrink-0" aria-hidden="true" />
          <span className={cn(nodo.tipo === "tematica" && "font-semibold")}>{nodo.etiqueta}</span>
          <span className="text-xs text-muted-foreground">{tipo.etiqueta}</span>
          <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold", nivel.claseInsignia)}>
            <nivel.Icono className="size-3" aria-hidden="true" />
            Nivel {nivel.etiqueta}
          </span>
          {!coincide && <span className="text-xs">(contexto, no coincide con el filtro)</span>}
        </button>
      </div>
      {hijos.length > 0 && (
        <ul id={`lista-hijos-${id}`} hidden={!abierto} className="ml-4 border-l pl-3">
          {hijos.map((hijo) => (
            <ItemLista key={hijo} id={hijo} ctx={ctx} />
          ))}
        </ul>
      )}
    </li>
  );
}

/** Alternativa accesible al grafo: la misma jerarquía en listas anidadas y expandibles. */
export function VistaLista({ ctx }: { ctx: ContextoLista }) {
  const raices = ctx.jerarquia.raices.filter((id) => !ctx.visibles || ctx.visibles.has(id));
  if (raices.length === 0) {
    return <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">Ningún elemento coincide con la búsqueda y el filtro.</p>;
  }
  return (
    <ul aria-label="Mapa mental en forma de lista" className="rounded-xl border p-3">
      {raices.map((id) => (
        <ItemLista key={id} id={id} ctx={ctx} />
      ))}
    </ul>
  );
}
