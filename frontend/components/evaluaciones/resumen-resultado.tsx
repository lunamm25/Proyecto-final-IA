import { formatearNota } from "@/components/portafolio/estado-entrega";
import type { Evaluacion } from "@/lib/tipos";

/** Nota tal como la envía el backend (el frontend no la calcula). */
export function NotaBackend({ nota }: { nota: number | null }) {
  if (nota === null) return <span className="text-sm text-muted-foreground">Sin nota</span>;
  return (
    <span>
      <span className="sr-only">Nota: </span>
      <strong className="text-3xl font-bold">{formatearNota(nota)}</strong>
      <span className="text-muted-foreground"> / 5,0</span>
    </span>
  );
}

function Lista({ titulo, elementos }: { titulo: string; elementos: string[] }) {
  if (elementos.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold">{titulo}</h3>
      <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
        {elementos.map((elemento, indice) => (
          <li key={`${indice}-${elemento}`}>{elemento}</li>
        ))}
      </ul>
    </div>
  );
}

/** Retroalimentación general (agrupada en `retroalimentacion`), aprendizajes y aspectos a fortalecer. */
export function ResumenResultado({ evaluacion }: { evaluacion: Evaluacion }) {
  const retro = evaluacion.retroalimentacion;
  return (
    <section aria-labelledby="titulo-resumen" className="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="titulo-resumen" className="text-lg font-semibold">Resultado general</h2>
        <NotaBackend nota={evaluacion.nota} />
      </div>
      {!retro ? (
        <p className="text-sm text-muted-foreground">Esta evaluación aún no tiene retroalimentación general.</p>
      ) : (
        <>
          {retro.retroalimentacion_general && <p className="text-sm">{retro.retroalimentacion_general}</p>}
          {retro.como_aplico_conocimientos && (
            <div>
              <h3 className="text-sm font-semibold">Cómo aplicó los conocimientos</h3>
              <p className="mt-1 text-sm">{retro.como_aplico_conocimientos}</p>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Lista titulo="Aprendizajes identificados" elementos={retro.aprendizajes_identificados} />
            <Lista titulo="Aspectos a fortalecer" elementos={retro.aspectos_a_fortalecer} />
          </div>
        </>
      )}
    </section>
  );
}
