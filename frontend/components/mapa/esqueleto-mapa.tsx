import { Loader2 } from "lucide-react";

function Bloque({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-xl bg-muted ${className}`} />;
}

/** Mensaje mientras el backend genera el mapa con IA (la primera vez puede tardar hasta ~60 s). */
export const MENSAJE_GENERANDO_MAPA = "Generando tu mapa mental, puede tardar hasta un minuto…";

/** Esqueleto con la forma del mapa mientras llegan los datos; con `mensaje` lo muestra de forma visible. */
export function EsqueletoMapa({ mensaje }: { mensaje?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-4">
      {mensaje && (
        <p className="flex items-center gap-2 rounded-lg border bg-muted/40 p-3 text-sm">
          <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden="true" />
          {mensaje}
        </p>
      )}
      <Bloque className="h-12 w-2/3" />
      <Bloque className="h-28" />
      <Bloque className="h-10" />
      <Bloque className="h-[65svh] min-h-96" />
      {!mensaje && <span className="sr-only">Cargando el mapa mental…</span>}
    </div>
  );
}
