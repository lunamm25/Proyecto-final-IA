import { CLASES_PRIORIDAD, TEXTO_PRIORIDAD } from "@/components/informe/formato-informe";
import type { AccionPlan, Prioridad } from "@/lib/tipos";

function EtiquetaPrioridad({ prioridad }: { prioridad: Prioridad }) {
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${CLASES_PRIORIDAD[prioridad]}`}>
      {TEXTO_PRIORIDAD[prioridad]}
    </span>
  );
}

function TarjetaAccion({ accion }: { accion: AccionPlan }) {
  return (
    <li className="rounded-lg border p-4 break-inside-avoid">
      <div className="flex flex-wrap items-center gap-2">
        <EtiquetaPrioridad prioridad={accion.prioridad} />
        <span className="text-xs text-muted-foreground">{accion.competencia}</span>
      </div>
      <p className="mt-2 font-medium">{accion.accion}</p>
      <p className="mt-1 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Recurso:</span> {accion.recurso}
      </p>
    </li>
  );
}

/** Plan personalizado de fortalecimiento redactado por la IA y validado por el backend. */
export function PlanFortalecimiento({ acciones }: { acciones: AccionPlan[] }) {
  if (acciones.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay acciones de fortalecimiento registradas.</p>;
  }
  return (
    <ul className="grid gap-3 md:grid-cols-2 print:grid-cols-2">
      {acciones.map((accion, indice) => (
        <TarjetaAccion key={`${accion.competencia}-${indice}`} accion={accion} />
      ))}
    </ul>
  );
}
