import { cn } from "@/lib/utils";
import { CLASES_ESTADO_EVALUACION, TEXTO_ESTADO_EVALUACION } from "@/components/evaluaciones/estado-evaluacion";
import type { EstadoEvaluacion } from "@/lib/tipos";

export function EtiquetaEstadoEvaluacion({ estado }: { estado: EstadoEvaluacion }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        CLASES_ESTADO_EVALUACION[estado],
      )}
    >
      {TEXTO_ESTADO_EVALUACION[estado]}
    </span>
  );
}
