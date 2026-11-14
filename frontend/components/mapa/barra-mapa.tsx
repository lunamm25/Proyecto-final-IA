"use client";

import { ChevronsDownUp, ChevronsUpDown, FileJson, ImageDown, Loader2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ESTILO_NIVEL } from "@/components/mapa/estilos-mapa";
import { NIVELES } from "@/components/mapa/grafo-mapa";
import type { NivelDominio } from "@/lib/tipos";

export type Descarga = "png" | "json";

interface PropsBarra {
  consulta: string;
  alBuscar: (texto: string) => void;
  niveles: ReadonlySet<NivelDominio>;
  alAlternarNivel: (nivel: NivelDominio) => void;
  alExpandirTodo: () => void;
  alColapsarTodo: () => void;
  alDescargar: (tipo: Descarga) => void;
  descargando: Descarga | null;
  pngDisponible: boolean;
}

function CampoBusqueda({ consulta, alBuscar }: Pick<PropsBarra, "consulta" | "alBuscar">) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1 sm:min-w-64">
      <label htmlFor="buscar-mapa" className="text-sm font-medium">
        Buscar por nombre
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <input
          id="buscar-mapa"
          type="search"
          value={consulta}
          onChange={(evento) => alBuscar(evento.target.value)}
          placeholder="Ej.: RAG, prompts, métricas…"
          className="h-9 w-full rounded-md border bg-background pr-3 pl-8 text-sm focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        />
      </div>
    </div>
  );
}

function FiltroNiveles({ niveles, alAlternarNivel }: Pick<PropsBarra, "niveles" | "alAlternarNivel">) {
  return (
    <fieldset className="flex flex-col gap-1">
      <legend className="mb-1 text-sm font-medium">Nivel de dominio</legend>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {NIVELES.map((nivel) => {
          const estilo = ESTILO_NIVEL[nivel];
          return (
            <label key={nivel} className="inline-flex min-h-9 cursor-pointer items-center gap-1.5 text-sm">
              <input type="checkbox" checked={niveles.has(nivel)} onChange={() => alAlternarNivel(nivel)} className="size-4 accent-primary" />
              <estilo.Icono className="size-4" aria-hidden="true" />
              {estilo.etiqueta}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function BotonesDescarga({ alDescargar, descargando, pngDisponible }: Pick<PropsBarra, "alDescargar" | "descargando" | "pngDisponible">) {
  const icono = (tipo: Descarga, Icono: typeof FileJson) =>
    descargando === tipo ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Icono aria-hidden="true" />;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="outline"
        onClick={() => alDescargar("png")}
        disabled={!pngDisponible || descargando !== null}
        aria-describedby={pngDisponible ? undefined : "ayuda-png"}
      >
        {icono("png", ImageDown)}
        {descargando === "png" ? "Generando PNG…" : "Descargar PNG"}
      </Button>
      <Button variant="outline" onClick={() => alDescargar("json")} disabled={descargando !== null}>
        {icono("json", FileJson)}
        Descargar JSON
      </Button>
      {!pngDisponible && (
        <span id="ayuda-png" className="text-xs text-muted-foreground">
          El PNG se genera desde la vista de grafo.
        </span>
      )}
    </div>
  );
}

/** Búsqueda, filtro por nivel, expandir/colapsar todo y descargas. Se envuelve en pantallas pequeñas. */
export function BarraMapa(props: PropsBarra) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border p-3">
      <div className="flex flex-wrap items-end gap-4">
        <CampoBusqueda consulta={props.consulta} alBuscar={props.alBuscar} />
        <FiltroNiveles niveles={props.niveles} alAlternarNivel={props.alAlternarNivel} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={props.alExpandirTodo}>
            <ChevronsUpDown aria-hidden="true" />
            Expandir todo
          </Button>
          <Button variant="secondary" onClick={props.alColapsarTodo}>
            <ChevronsDownUp aria-hidden="true" />
            Colapsar todo
          </Button>
        </div>
        <BotonesDescarga alDescargar={props.alDescargar} descargando={props.descargando} pngDisponible={props.pngDisponible} />
      </div>
    </div>
  );
}
