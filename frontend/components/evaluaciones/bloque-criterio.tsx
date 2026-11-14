import { ListaEvidencias } from "@/components/evaluaciones/lista-evidencias";
import type { CriterioRubrica, EvaluacionCriterio } from "@/lib/tipos";

/** Cuándo mostrar el nivel propuesto por la IA: siempre (revisión), solo si difiere (docente) u oculto (estudiante). */
export type ModoNivelIa = "siempre" | "si_difiere" | "oculto";

interface BloqueCriterioProps {
  criterio: EvaluacionCriterio;
  criterioRubrica?: CriterioRubrica;
  modoNivelIa: ModoNivelIa;
  /** Muestra el motivo del último ajuste del docente (solo docente/admin). */
  mostrarAjuste: boolean;
  /** Espacio para el formulario de ajuste en la vista de revisión. */
  children?: React.ReactNode;
}

function ListaTexto({ titulo, elementos }: { titulo: string; elementos: string[] }) {
  return (
    <div>
      <h4 className="text-sm font-semibold">{titulo}</h4>
      {elementos.length === 0 ? (
        <p className="mt-1 text-sm text-muted-foreground">Sin registros.</p>
      ) : (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
          {elementos.map((elemento) => (
            <li key={elemento}>{elemento}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Niveles({ criterio, modoNivelIa }: { criterio: EvaluacionCriterio; modoNivelIa: ModoNivelIa }) {
  const difiere = criterio.nivel_ia !== criterio.nivel_final;
  const verIa = modoNivelIa === "siempre" || (modoNivelIa === "si_difiere" && difiere);
  return (
    <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
      {verIa && (
        <div className="flex gap-1">
          <dt className="text-muted-foreground">Propuesto por la IA:</dt>
          <dd className="font-medium">{criterio.nivel_ia}</dd>
        </div>
      )}
      <div className="flex gap-1">
        <dt className="text-muted-foreground">{verIa ? "Nivel final:" : "Nivel:"}</dt>
        <dd className="font-semibold">{criterio.nivel_final}</dd>
      </div>
      {verIa && difiere && (
        <div className="flex gap-1">
          <dt className="sr-only">Ajuste:</dt>
          <dd className="text-xs font-medium text-amber-800">Ajustado por el docente</dd>
        </div>
      )}
    </dl>
  );
}

/** Resultado de un criterio con sus evidencias. Se comparte entre la vista del estudiante y la revisión docente. */
export function BloqueCriterio({ criterio, criterioRubrica, modoNivelIa, mostrarAjuste, children }: BloqueCriterioProps) {
  const nombre = criterio.nombre || criterioRubrica?.nombre || criterio.criterio_id;
  const competencia = criterio.competencia || criterioRubrica?.competencia || "";
  const ponderacion = criterio.ponderacion || criterioRubrica?.ponderacion;
  const idTitulo = `criterio-${criterio.criterio_id}`;

  return (
    <article aria-labelledby={idTitulo} className="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <header className="space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 id={idTitulo} className="text-base font-semibold">{nombre}</h3>
          {ponderacion !== undefined && (
            <span className="text-xs text-muted-foreground">Ponderación: {ponderacion} %</span>
          )}
        </div>
        {competencia && <p className="text-xs text-muted-foreground">Competencia: {competencia}</p>}
        <Niveles criterio={criterio} modoNivelIa={modoNivelIa} />
      </header>

      {mostrarAjuste && criterio.ajuste_docente && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <span className="font-semibold">Motivo del ajuste docente: </span>
          {criterio.ajuste_docente}
        </p>
      )}

      <div>
        <h4 className="mb-2 text-sm font-semibold">Evidencias</h4>
        <ListaEvidencias evidencias={criterio.evidencias} />
      </div>

      <div>
        <h4 className="text-sm font-semibold">Justificación</h4>
        <p className="mt-1 text-sm">{criterio.justificacion}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <ListaTexto titulo="Fortalezas" elementos={criterio.fortalezas} />
        <ListaTexto titulo="Debilidades" elementos={criterio.debilidades} />
      </div>

      <div>
        <h4 className="text-sm font-semibold">Recomendación</h4>
        <p className="mt-1 text-sm">{criterio.recomendacion}</p>
      </div>

      {children}
    </article>
  );
}
