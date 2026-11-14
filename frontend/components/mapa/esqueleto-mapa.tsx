function Bloque({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-xl bg-muted ${className}`} />;
}

/** Esqueleto con la forma del mapa mientras llegan los datos. */
export function EsqueletoMapa() {
  return (
    <div role="status" aria-label="Cargando el mapa mental…" className="space-y-4">
      <Bloque className="h-12 w-2/3" />
      <Bloque className="h-28" />
      <Bloque className="h-10" />
      <Bloque className="h-[65svh] min-h-96" />
      <span className="sr-only">Cargando el mapa mental…</span>
    </div>
  );
}
