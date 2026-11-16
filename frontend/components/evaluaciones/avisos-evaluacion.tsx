import Link from "next/link";
import { AlertTriangle, Clock } from "lucide-react";

const CLASE_ENLACE = "mt-4 inline-block text-sm font-medium underline underline-offset-4";

/** Lo único que ve el estudiante mientras la evaluación no está publicada (RF-05 CA6, RF-07 CA3). */
export function PendienteRevision() {
  return (
    <section role="status" className="mx-auto my-12 max-w-lg rounded-xl border border-amber-300 bg-amber-50 p-6 text-center">
      <Clock className="mx-auto size-8 text-amber-700" aria-hidden="true" />
      <h2 className="mt-3 text-lg font-semibold text-amber-900">Pendiente de revisión docente</h2>
      <p className="mt-2 text-sm text-amber-900">
        Tu docente está revisando esta evaluación. Podrás ver la nota y la retroalimentación cuando la publique.
      </p>
      <Link href="/portafolio" className={CLASE_ENLACE}>
        Volver a mi portafolio
      </Link>
    </section>
  );
}

interface ErrorEvaluacionProps {
  /** Detalle técnico del backend; solo se muestra a docentes y administradores. */
  detalle: string | null;
  esEstudiante: boolean;
  enlaceRevision?: string;
}

/** Estado "error" de la evaluación (RF-05 CA4). */
export function ErrorEvaluacion({ detalle, esEstudiante, enlaceRevision }: ErrorEvaluacionProps) {
  return (
    <section role="alert" className="mx-auto my-12 max-w-lg rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center">
      <AlertTriangle className="mx-auto size-8 text-destructive" aria-hidden="true" />
      <h2 className="mt-3 text-lg font-semibold">No se pudo completar la evaluación</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {esEstudiante
          ? "La evaluación automática de tu laboratorio falló. Puedes solicitarla de nuevo desde tu portafolio o avisar a tu docente."
          : "La evaluación automática terminó con error. El detalle que reportó el sistema es:"}
      </p>
      {!esEstudiante && (
        <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-muted p-3 text-left text-xs whitespace-pre-wrap">
          {detalle ?? "El backend no envió el detalle del error."}
        </pre>
      )}
      {esEstudiante ? (
        <Link href="/portafolio" className={CLASE_ENLACE}>
          Ir a mi portafolio
        </Link>
      ) : (
        enlaceRevision && (
          <Link href={enlaceRevision} className={CLASE_ENLACE}>
            Ir a la revisión
          </Link>
        )
      )}
    </section>
  );
}
