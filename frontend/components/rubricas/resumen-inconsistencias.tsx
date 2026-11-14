import { AlertTriangle, CheckCircle2, Server } from "lucide-react";
import type { Inconsistencia } from "@/lib/tipos";

export interface ResultadoServidor {
  origen: "extraccion" | "validacion";
  inconsistencias: Inconsistencia[];
}

interface ResumenInconsistenciasProps {
  inconsistencias: Inconsistencia[];
  camposVacios: string[];
  servidor: ResultadoServidor | null;
}

function ListaMensajes({ mensajes }: { mensajes: string[] }) {
  return (
    <ul className="mt-2 list-disc space-y-0.5 pl-5">
      {mensajes.map((mensaje, i) => (
        <li key={`${i}-${mensaje}`}>{mensaje}</li>
      ))}
    </ul>
  );
}

function BloqueServidor({ servidor }: { servidor: ResultadoServidor }) {
  const titulo = servidor.origen === "extraccion" ? "Inconsistencias reportadas al extraer" : "Resultado del servidor";
  const vacio = servidor.inconsistencias.length === 0;
  return (
    <div className="rounded-lg border bg-muted/40 p-3 text-sm">
      <p className="flex items-center gap-1 font-medium">
        <Server className="size-4" aria-hidden="true" />
        {titulo}
      </p>
      {vacio ? (
        <p className="mt-1 text-emerald-700">El servidor no encontró inconsistencias.</p>
      ) : (
        <ListaMensajes mensajes={servidor.inconsistencias.map((i) => i.mensaje)} />
      )}
    </div>
  );
}

/** Resumen de todas las inconsistencias calculadas en vivo, más el último resultado del servidor. */
export function ResumenInconsistencias({ inconsistencias, camposVacios, servidor }: ResumenInconsistenciasProps) {
  const total = inconsistencias.length + camposVacios.length;
  return (
    <section aria-labelledby="titulo-resumen" className="space-y-3 rounded-xl border p-4">
      <h2 id="titulo-resumen" className="font-semibold">
        Revisión de la rúbrica
      </h2>
      <p className="text-xs text-muted-foreground">
        Esta revisión se calcula en tu navegador mientras editas. La validación oficial la hace el servidor al guardar.
      </p>
      <div aria-live="polite">
        {total === 0 ? (
          <p className="flex items-center gap-1 text-sm text-emerald-700">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            Sin inconsistencias: la rúbrica se puede aprobar.
          </p>
        ) : (
          <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="flex items-center gap-1 font-medium">
              <AlertTriangle className="size-4" aria-hidden="true" />
              {total === 1 ? "1 problema por corregir" : `${total} problemas por corregir`} antes de aprobar
            </p>
            <ListaMensajes mensajes={[...camposVacios, ...inconsistencias.map((i) => i.mensaje)]} />
          </div>
        )}
      </div>
      {servidor && <BloqueServidor servidor={servidor} />}
    </section>
  );
}
