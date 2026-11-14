function Bloque({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-xl bg-muted ${className}`} />;
}

/** Esqueleto con la forma del informe mientras llegan los datos. */
export function EsqueletoInforme() {
  return (
    <div role="status" aria-label="Cargando el informe…" className="space-y-6">
      <Bloque className="h-16 w-2/3" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Bloque key={i} className="h-24" />
        ))}
      </div>
      <Bloque className="h-80" />
      <Bloque className="h-72" />
      <span className="sr-only">Cargando el informe…</span>
    </div>
  );
}
