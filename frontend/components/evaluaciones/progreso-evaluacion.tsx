import { Loader2 } from "lucide-react";
import { INTERVALO_SONDEO_MS, MAX_FALLOS_SONDEO } from "@/components/evaluaciones/estado-evaluacion";

const PASOS = [
  "Extraer el texto del informe",
  "Preparar y verificar el código",
  "Evaluar cada criterio con la IA",
  "Verificar las evidencias citadas",
];

/** Indicador de progreso mientras el backend procesa la evaluación (RNF-04). */
export function ProgresoEvaluacion({ fallos }: { fallos: number }) {
  return (
    <section
      aria-labelledby="titulo-progreso"
      className="mx-auto my-10 max-w-xl rounded-xl border bg-card p-6"
    >
      <div className="flex items-center gap-3">
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
        <h2 id="titulo-progreso" className="text-lg font-semibold">
          Evaluando el laboratorio…
        </h2>
      </div>
      <div
        role="progressbar"
        aria-label="Progreso de la evaluación"
        aria-valuetext="En proceso"
        className="mt-4 h-2 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
      </div>
      <p aria-live="polite" className="mt-4 text-sm text-muted-foreground">
        La evaluación se está procesando. Esta página se actualiza sola cada {INTERVALO_SONDEO_MS / 1000} segundos;
        suele tardar menos de 2 minutos.
      </p>
      <ol className="mt-4 list-decimal space-y-1 pl-5 text-sm">
        {PASOS.map((paso) => (
          <li key={paso}>{paso}</li>
        ))}
      </ol>
      {fallos > 0 && (
        <p role="status" className="mt-4 text-sm text-amber-800">
          No pudimos consultar el estado (intento {fallos} de {MAX_FALLOS_SONDEO}). Volveremos a intentarlo.
        </p>
      )}
    </section>
  );
}
