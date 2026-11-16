import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { textoFuente } from "@/components/evaluaciones/estado-evaluacion";
import type { Cita } from "@/lib/tipos";

function MarcaVerificacion({ verificada }: { verificada: boolean }) {
  if (verificada) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-800">
        <CheckCircle2 className="size-3.5" aria-hidden="true" />
        Verificada
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-red-300 bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-800">
      <AlertTriangle className="size-3.5" aria-hidden="true" />
      No verificada
    </span>
  );
}

/** Similitud que calculó el backend, ya en escala de 0 a 100. */
function textoSimilitud(similitud: number): string {
  return `similitud ${Math.round(similitud)} %`;
}

/** Una cita solo cuenta como verificada si el backend envía `verificada: true` (cualquier otro valor = no verificada). */
function estaVerificada(cita: Cita): boolean {
  return cita.verificada === true;
}

function ItemCita({ cita }: { cita: Cita }) {
  const verificada = estaVerificada(cita);
  return (
    <li className={cn("rounded-lg border p-3", verificada ? "bg-muted/30" : "border-red-300 border-l-4 bg-red-50/60")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">
          {textoFuente(cita.fuente)}
          {cita.ubicacion && ` · ${cita.ubicacion}`}
          {` · ${textoSimilitud(cita.similitud)}`}
        </span>
        <MarcaVerificacion verificada={verificada} />
      </div>
      <blockquote className="mt-2 border-l-2 pl-3 text-sm italic break-words">“{cita.fragmento}”</blockquote>
      {!verificada && (
        <p className="mt-2 text-xs text-red-800">
          Esta cita no se encontró en el material entregado: puede ser una alucinación de la IA.
        </p>
      )}
    </li>
  );
}

/** Texto cuando el criterio no trae citas: sin ningún indicador de verificación. */
export const TEXTO_SIN_EVIDENCIA = "Sin evidencia en la entrega";

/**
 * Citas de un criterio con su verificación anti-alucinación (RF-05 CA3). Se usa en la vista del estudiante y en la
 * revisión docente. Con `citas: []` solo muestra "Sin evidencia en la entrega": nada de "verificada".
 */
export function ListaCitas({ citas }: { citas: Cita[] }) {
  if (citas.length === 0) {
    return <p className="text-sm text-muted-foreground">{TEXTO_SIN_EVIDENCIA}</p>;
  }
  const noVerificadas = citas.filter((c) => !estaVerificada(c)).length;
  return (
    <div>
      {noVerificadas > 0 && (
        <p className="mb-2 text-xs font-medium text-red-800">
          {noVerificadas === 1 ? "1 evidencia no verificada" : `${noVerificadas} evidencias no verificadas`}
        </p>
      )}
      <ul className="space-y-2">
        {citas.map((cita, indice) => (
          <ItemCita key={`${cita.fuente}-${indice}`} cita={cita} />
        ))}
      </ul>
    </div>
  );
}
