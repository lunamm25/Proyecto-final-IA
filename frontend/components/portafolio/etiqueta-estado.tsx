import { cn } from "@/lib/utils";
import { CLASES_ESTADO, TEXTO_ESTADO, type EstadoLaboratorio } from "@/components/portafolio/estado-entrega";

export function EtiquetaEstado({ estado }: { estado: EstadoLaboratorio }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        CLASES_ESTADO[estado],
      )}
    >
      {TEXTO_ESTADO[estado]}
    </span>
  );
}
