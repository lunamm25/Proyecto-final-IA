import { cn } from "@/lib/utils";
import { CLASES_ESTADO_EVALUACION, TEXTO_ESTADO_EVALUACION } from "@/components/evaluaciones/estado-evaluacion";
import type { EstadoEvaluacion } from "@/lib/tipos";

export function EtiquetaEstadoEvaluacion({ estado, procesando = false }: { estado: EstadoEvaluacion; procesando?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        procesando ? "border-sky-300 bg-sky-50 text-sky-800" : CLASES_ESTADO_EVALUACION[estado],
      )}
    >
      {procesando ? "Procesando" : TEXTO_ESTADO_EVALUACION[estado]}
    </span>
  );
}
