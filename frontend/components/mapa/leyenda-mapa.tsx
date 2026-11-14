import { ESTILO_NIVEL, ESTILO_TIPO } from "@/components/mapa/estilos-mapa";
import { NIVELES } from "@/components/mapa/grafo-mapa";
import type { TipoNodo } from "@/lib/tipos";
import { cn } from "@/lib/utils";

const TIPOS: TipoNodo[] = ["tematica", "concepto", "laboratorio"];

/** Leyenda: color + icono + texto por nivel, forma por tipo y estilo de las líneas. */
export function LeyendaMapa() {
  return (
    <section aria-labelledby="titulo-leyenda" className="rounded-xl border p-3 text-sm">
      <h2 id="titulo-leyenda" className="sr-only">
        Leyenda del mapa
      </h2>
      <div className="flex flex-wrap gap-x-6 gap-y-3">
        <ul className="flex flex-wrap items-center gap-2" aria-label="Niveles de dominio">
          {NIVELES.map((nivel) => {
            const estilo = ESTILO_NIVEL[nivel];
            return (
              <li key={nivel} className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold", estilo.claseInsignia)}>
                <estilo.Icono className="size-3.5" aria-hidden="true" />
                {estilo.etiqueta}
              </li>
            );
          })}
        </ul>
        <ul className="flex flex-wrap items-center gap-3 text-xs" aria-label="Tipos de nodo">
          {TIPOS.map((tipo) => {
            const estilo = ESTILO_TIPO[tipo];
            return (
              <li key={tipo} className="inline-flex items-center gap-1.5">
                <span className={cn("inline-flex size-5 items-center justify-center border-foreground/60", estilo.claseForma, "p-0")}>
                  <estilo.Icono className="size-3" aria-hidden="true" />
                </span>
                {estilo.etiqueta}
              </li>
            );
          })}
        </ul>
        <ul className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground" aria-label="Líneas">
          <li className="inline-flex items-center gap-1.5">
            <span className="inline-block w-6 border-t-2 border-muted-foreground" aria-hidden="true" />
            Pertenece a
          </li>
          <li className="inline-flex items-center gap-1.5">
            <span className="inline-block w-6 border-t-2 border-dashed border-muted-foreground" aria-hidden="true" />
            Relación adicional
          </li>
        </ul>
      </div>
    </section>
  );
}
