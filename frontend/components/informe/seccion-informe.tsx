import type { ReactNode } from "react";

interface SeccionInformeProps {
  id: string;
  titulo: string;
  descripcion?: string;
  /** Evita que la sección se corte entre páginas al imprimir (solo para secciones cortas). */
  sinCorte?: boolean;
  children: ReactNode;
}

export function SeccionInforme({ id, titulo, descripcion, sinCorte = false, children }: SeccionInformeProps) {
  return (
    <section
      aria-labelledby={id}
      className={`rounded-xl border bg-card p-4 sm:p-6 print:p-4 ${sinCorte ? "break-inside-avoid" : ""}`}
    >
      <h2 id={id} className="text-lg font-semibold break-after-avoid">
        {titulo}
      </h2>
      {descripcion && <p className="mt-1 text-sm text-muted-foreground">{descripcion}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}
