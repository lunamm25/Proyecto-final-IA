"use client";

import Link from "next/link";
import { Cargando, EstadoVacio, MensajeError } from "@/components/estados";
import { useSesion } from "@/components/proveedor-sesion";
import { ErrorEvaluacion, PendienteRevision } from "@/components/evaluaciones/avisos-evaluacion";
import { BloqueCriterio } from "@/components/evaluaciones/bloque-criterio";
import { EtiquetaEstadoEvaluacion } from "@/components/evaluaciones/etiqueta-estado-evaluacion";
import { ProgresoEvaluacion } from "@/components/evaluaciones/progreso-evaluacion";
import { ResumenResultado } from "@/components/evaluaciones/resumen-resultado";
import { buscarCriterioRubrica, estaProcesando, formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import {
  useContextoEvaluacion,
  useReferenciasEvaluacion,
  type ContextoEvaluacion,
  type Referencias,
} from "@/components/evaluaciones/use-contexto-evaluacion";
import { rutaRevision } from "@/lib/rutas-evaluacion";
import { useSondeoEvaluacion } from "@/components/evaluaciones/use-sondeo-evaluacion";
import { idDesdeUrl, type Evaluacion, type IdNumerico } from "@/lib/tipos";

const CLASE_ENLACE_BOTON =
  "inline-flex h-8 items-center justify-center rounded-lg border px-3 text-sm font-medium hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 outline-none";

interface DetalleProps {
  evaluacion: Evaluacion;
  contexto: ContextoEvaluacion;
  referencias: Referencias;
  esDocente: boolean;
}

/** Sin laboratorio no hay rúbrica: los criterios se muestran por su id. */
function AvisoSinLaboratorio() {
  return (
    <p role="note" className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
      No se pudo identificar el laboratorio de esta evaluación, así que los criterios se muestran por su código. Ábrela
      desde el portafolio o la bandeja de revisión para ver sus nombres.
    </p>
  );
}

function Cabecera({ evaluacion, contexto, referencias, esDocente }: DetalleProps) {
  const fecha = evaluacion.publicada_en ?? evaluacion.creada_en;
  return (
    <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {contexto.laboratorio && (
          <p className="font-mono text-xs text-muted-foreground">{contexto.laboratorio.codigo}</p>
        )}
        <h1 className="text-2xl font-bold">{contexto.laboratorio?.titulo ?? "Evaluación del laboratorio"}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {evaluacion.publicada_en ? "Publicada el " : "Generada el "}
          {formatearFechaHora(fecha)}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <EtiquetaEstadoEvaluacion estado={evaluacion.estado} />
        {esDocente && (
          <Link href={rutaRevision(evaluacion.id, referencias)} className={CLASE_ENLACE_BOTON}>
            Revisar
          </Link>
        )}
      </div>
    </header>
  );
}

function DetalleEvaluacion({ evaluacion, contexto, referencias, esDocente }: DetalleProps) {
  return (
    <div className="space-y-6">
      <Cabecera evaluacion={evaluacion} contexto={contexto} referencias={referencias} esDocente={esDocente} />
      {referencias.laboratorioId === null && <AvisoSinLaboratorio />}
      {esDocente && evaluacion.estado !== "publicada" && (
        <p role="note" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          Esta evaluación aún no está publicada: el estudiante solo ve “Pendiente de revisión docente”.
        </p>
      )}
      <ResumenResultado evaluacion={evaluacion} />
      <section aria-labelledby="titulo-criterios" className="space-y-4">
        <h2 id="titulo-criterios" className="text-lg font-semibold">Resultado por criterio</h2>
        {evaluacion.criterios.length === 0 ? (
          <EstadoVacio titulo="Sin criterios" mensaje="Esta evaluación no tiene resultados por criterio." />
        ) : (
          evaluacion.criterios.map((criterio) => (
            <BloqueCriterio
              key={criterio.criterio_id}
              criterio={criterio}
              criterioRubrica={buscarCriterioRubrica(contexto.rubrica?.contenido ?? null, criterio.criterio_id)}
              modoNivelIa={esDocente ? "si_difiere" : "oculto"}
              mostrarAjuste={esDocente}
            />
          ))
        )}
      </section>
    </div>
  );
}

function ContenidoListo({ evaluacion, esEstudiante, fallos }: { evaluacion: Evaluacion; esEstudiante: boolean; fallos: number }) {
  const publicadaOVisible = !esEstudiante || evaluacion.estado === "publicada";
  const referencias = useReferenciasEvaluacion(evaluacion);
  const contexto = useContextoEvaluacion(publicadaOVisible ? referencias.laboratorioId : null);

  if (estaProcesando(evaluacion)) return <ProgresoEvaluacion fallos={fallos} />;
  if (evaluacion.estado === "error") {
    return (
      <ErrorEvaluacion detalle={evaluacion.error} esEstudiante={esEstudiante} enlaceRevision={rutaRevision(evaluacion.id, referencias)} />
    );
  }
  if (!publicadaOVisible) return <PendienteRevision />;
  return <DetalleEvaluacion evaluacion={evaluacion} contexto={contexto} referencias={referencias} esDocente={!esEstudiante} />;
}

/** /evaluaciones/[id]: progreso, resultado publicado (estudiante) o resultado completo (docente/admin). */
export function VistaEvaluacion({ id }: { id: string }) {
  const idNumerico = idDesdeUrl(id);
  if (idNumerico === null) {
    return <MensajeError titulo="Evaluación no encontrada" mensaje="La dirección no corresponde a ninguna evaluación." />;
  }
  return <VistaEvaluacionValida id={idNumerico} />;
}

function VistaEvaluacionValida({ id }: { id: IdNumerico }) {
  const { perfil } = useSesion();
  const esEstudiante = perfil?.rol === "estudiante";
  const { estado, reintentar } = useSondeoEvaluacion(id);

  if (estado.tipo === "cargando") return <Cargando texto="Cargando la evaluación…" />;
  if (estado.tipo === "error") {
    if (esEstudiante && (estado.status === 403 || estado.status === 404)) return <PendienteRevision />;
    return <MensajeError titulo="No se pudo cargar la evaluación" mensaje={estado.mensaje} alReintentar={reintentar} />;
  }
  return <ContenidoListo evaluacion={estado.evaluacion} esEstudiante={esEstudiante} fallos={estado.fallos} />;
}
