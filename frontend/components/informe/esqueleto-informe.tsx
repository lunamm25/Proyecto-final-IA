import { Loader2 } from "lucide-react";

function Bloque({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-xl bg-muted ${className}`} />;
}

/** Mensaje mientras el backend genera el informe con IA (la primera vez puede tardar hasta ~60 s). */
export const MENSAJE_GENERANDO_INFORME = "Generando tu informe, puede tardar hasta un minuto…";

/** Esqueleto con la forma del informe mientras llegan los datos; con `mensaje` lo muestra de forma visible. */
export function EsqueletoInforme({ mensaje }: { mensaje?: string }) {
  const texto = mensaje ?? "Cargando el informe…";
  return (
    <div role="status" aria-live="polite" className="space-y-6">
      {mensaje && (
        <p className="flex items-center gap-2 rounded-lg border bg-muted/40 p-3 text-sm">
          <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden="true" />
          {mensaje}
        </p>
      )}
      <Bloque className="h-16 w-2/3" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Bloque key={i} className="h-24" />
        ))}
      </div>
      <Bloque className="h-80" />
      <Bloque className="h-72" />
      {!mensaje && <span className="sr-only">{texto}</span>}
    </div>
  );
}
