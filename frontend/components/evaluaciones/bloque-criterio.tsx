import { ListaCitas } from "@/components/evaluaciones/lista-evidencias";
import type { CriterioRubrica, EvaluacionCriterio, RetroalimentacionCriterioIA } from "@/lib/tipos";

/** Cuándo mostrar el nivel propuesto por la IA: siempre (revisión), solo si difiere (docente) u oculto (estudiante). */
export type ModoNivelIa = "siempre" | "si_difiere" | "oculto";

const SIN_TEXTO = "Sin registro.";

interface BloqueCriterioProps {
  criterio: EvaluacionCriterio;
  /** Criterio de la rúbrica con el mismo id: aporta nombre, competencia y ponderación. */
  criterioRubrica?: CriterioRubrica;
  modoNivelIa: ModoNivelIa;
  /** Muestra el motivo del ajuste y los textos originales de la IA (solo docente/admin). */
  mostrarAjuste: boolean;
  /** Espacio para los formularios de ajuste y edición en la vista de revisión. */
  children?: React.ReactNode;
}

function ListaTexto({ titulo, elementos }: { titulo: string; elementos: string[] }) {
  return (
    <div>
      <h4 className="text-sm font-semibold">{titulo}</h4>
      {elementos.length === 0 ? (
        <p className="mt-1 text-sm text-muted-foreground">{SIN_TEXTO}</p>
      ) : (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
          {elementos.map((elemento, indice) => (
            <li key={`${indice}-${elemento}`}>{elemento}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Parrafo({ titulo, texto }: { titulo: string; texto: string | null }) {
  return (
    <div>
      <h4 className="text-sm font-semibold">{titulo}</h4>
      <p className={texto ? "mt-1 text-sm" : "mt-1 text-sm text-muted-foreground"}>{texto || SIN_TEXTO}</p>
    </div>
  );
}

function Niveles({ criterio, modoNivelIa }: { criterio: EvaluacionCriterio; modoNivelIa: ModoNivelIa }) {
  const difiere = criterio.nivel_ia !== null && criterio.nivel_ia !== criterio.nivel_final;
  const verIa = criterio.nivel_ia !== null && (modoNivelIa === "siempre" || (modoNivelIa === "si_difiere" && difiere));
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
        <dd className="font-semibold">{criterio.nivel_final ?? "Sin nivel asignado"}</dd>
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

function textosEditados(criterio: EvaluacionCriterio, original: RetroalimentacionCriterioIA): boolean {
  return (
    original.justificacion !== criterio.justificacion ||
    original.recomendacion !== criterio.recomendacion ||
    original.fortalezas.join("\n") !== criterio.fortalezas.join("\n") ||
    original.debilidades.join("\n") !== criterio.debilidades.join("\n")
  );
}

/** Textos que propuso la IA, para que el docente compare con los editados. */
function OriginalIa({ original }: { original: RetroalimentacionCriterioIA }) {
  return (
    <details className="rounded-lg border border-dashed p-3 text-sm">
      <summary className="cursor-pointer font-medium">Ver la propuesta original de la IA</summary>
      <div className="mt-3 space-y-3">
        <Parrafo titulo="Justificación" texto={original.justificacion} />
        <div className="grid gap-4 sm:grid-cols-2">
          <ListaTexto titulo="Fortalezas" elementos={original.fortalezas} />
          <ListaTexto titulo="Debilidades" elementos={original.debilidades} />
        </div>
        <Parrafo titulo="Recomendación" texto={original.recomendacion} />
      </div>
    </details>
  );
}

/** Resultado de un criterio con sus citas. Se comparte entre la vista del estudiante y la revisión docente. */
export function BloqueCriterio({ criterio, criterioRubrica, modoNivelIa, mostrarAjuste, children }: BloqueCriterioProps) {
  const nombre = criterioRubrica?.nombre || `Criterio ${criterio.criterio_id}`;
  const idTitulo = `criterio-${criterio.criterio_id}`;
  const original = mostrarAjuste ? criterio.original_ia : null;

  return (
    <article aria-labelledby={idTitulo} className="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <header className="space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 id={idTitulo} className="text-base font-semibold">{nombre}</h3>
          {criterioRubrica && (
            <span className="text-xs text-muted-foreground">Ponderación: {criterioRubrica.ponderacion} %</span>
          )}
        </div>
        {criterioRubrica?.competencia && (
          <p className="text-xs text-muted-foreground">Competencia: {criterioRubrica.competencia}</p>
        )}
        <Niveles criterio={criterio} modoNivelIa={modoNivelIa} />
      </header>

      {mostrarAjuste && criterio.ajuste_docente && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <span className="font-semibold">Motivo del ajuste docente: </span>
          {criterio.ajuste_docente}
        </p>
      )}

      <div>
        <h4 className="mb-2 text-sm font-semibold">Evidencias citadas</h4>
        <ListaCitas citas={criterio.citas} />
      </div>

      <Parrafo titulo="Justificación" texto={criterio.justificacion} />

      <div className="grid gap-4 sm:grid-cols-2">
        <ListaTexto titulo="Fortalezas" elementos={criterio.fortalezas} />
        <ListaTexto titulo="Debilidades" elementos={criterio.debilidades} />
      </div>

      <Parrafo titulo="Recomendación" texto={criterio.recomendacion} />

      {original && textosEditados(criterio, original) && <OriginalIa original={original} />}

      {children}
    </article>
  );
}
