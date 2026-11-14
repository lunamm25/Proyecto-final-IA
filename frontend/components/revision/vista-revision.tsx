"use client";

import Link from "next/link";
import { useCallback } from "react";
import { Cargando, EstadoVacio, MensajeError } from "@/components/estados";
import { ErrorEvaluacion } from "@/components/evaluaciones/avisos-evaluacion";
import { BloqueCriterio } from "@/components/evaluaciones/bloque-criterio";
import { EtiquetaEstadoEvaluacion } from "@/components/evaluaciones/etiqueta-estado-evaluacion";
import { ProgresoEvaluacion } from "@/components/evaluaciones/progreso-evaluacion";
import { NotaBackend, ResumenResultado } from "@/components/evaluaciones/resumen-resultado";
import {
  TEXTO_ESTADO_EVALUACION,
  admiteAjustes,
  buscarCriterioRubrica,
  estaProcesando,
  formatearFechaHora,
} from "@/components/evaluaciones/estado-evaluacion";
import { useContextoEvaluacion, type ContextoEvaluacion } from "@/components/evaluaciones/use-contexto-evaluacion";
import { useSondeoEvaluacion } from "@/components/evaluaciones/use-sondeo-evaluacion";
import { AccionesRevision } from "@/components/revision/acciones-revision";
import { FormularioAjuste } from "@/components/revision/formulario-ajuste";
import { PanelTraza } from "@/components/revision/panel-traza";
import { PanelVerificacion } from "@/components/revision/panel-verificacion";
import { useNombreEstudiante } from "@/components/revision/use-nombre-estudiante";
import { obtenerTraza } from "@/lib/api";
import { idDesdeUrl, type Evaluacion, type IdNumerico } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

const ENLACE_BANDEJA = (
  <Link href="/docente/revision" className="text-sm font-medium underline underline-offset-4">
    ← Volver a la bandeja
  </Link>
);

const CLASE_ENLACE_ESTUDIANTE =
  "inline-flex h-8 items-center justify-center rounded-lg border px-3 text-sm font-medium transition-colors hover:bg-muted outline-none focus-visible:ring-3 focus-visible:ring-ring/50";

/** Enlaces al informe y al mapa mental del estudiante de la evaluación. */
function EnlacesEstudiante({ estudianteId }: { estudianteId: string }) {
  const id = encodeURIComponent(estudianteId);
  return (
    <nav aria-label="Aprendizaje del estudiante" className="mt-3 flex flex-wrap gap-2">
      <Link href={`/informe/${id}`} className={CLASE_ENLACE_ESTUDIANTE}>
        Ver informe
      </Link>
      <Link href={`/mapa/${id}`} className={CLASE_ENLACE_ESTUDIANTE}>
        Ver mapa
      </Link>
    </nav>
  );
}

interface CabeceraProps {
  evaluacion: Evaluacion;
  contexto: ContextoEvaluacion;
  alCambiar: (evaluacion: Evaluacion) => void;
}

function Cabecera({ evaluacion, contexto, alCambiar }: CabeceraProps) {
  const nombre = useNombreEstudiante(evaluacion.estudiante_id);
  return (
    <header className="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-xs text-muted-foreground">{contexto.laboratorio?.codigo ?? evaluacion.laboratorio_id}</p>
          <h1 className="text-2xl font-bold">{contexto.laboratorio?.titulo ?? "Revisión de la evaluación"}</h1>
          <p className="mt-1 text-sm">Estudiante: <span className="font-medium">{nombre ?? evaluacion.estudiante_id}</span></p>
          <p className="text-sm text-muted-foreground">Generada el {formatearFechaHora(evaluacion.creada_en)}</p>
          <EnlacesEstudiante estudianteId={evaluacion.estudiante_id} />
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <EtiquetaEstadoEvaluacion estado={evaluacion.estado} />
          <NotaBackend nota={evaluacion.nota} />
        </div>
      </div>
      <AccionesRevision evaluacion={evaluacion} alCambiar={alCambiar} />
    </header>
  );
}

function bloqueoAjuste(evaluacion: Evaluacion): string | null {
  if (admiteAjustes(evaluacion)) return null;
  return `La evaluación está ${TEXTO_ESTADO_EVALUACION[evaluacion.estado].toLowerCase()}: ya no se pueden ajustar los niveles.`;
}

function AvisoVersionRubrica({ evaluacion, contexto }: { evaluacion: Evaluacion; contexto: ContextoEvaluacion }) {
  if (!contexto.cargado) return null;
  if (!contexto.rubrica) {
    return (
      <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
        No se pudo cargar la rúbrica del laboratorio{contexto.errorRubrica ? `: ${contexto.errorRubrica}` : "."} Sin ella no se
        pueden ajustar niveles.
      </p>
    );
  }
  if (contexto.rubrica.version === evaluacion.rubrica_version) return null;
  return (
    <p role="note" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      La evaluación se hizo con la rúbrica v{evaluacion.rubrica_version}, pero la vigente es la v{contexto.rubrica.version}.
      Los niveles del selector son los de la versión vigente; el sistema rechazará un nivel que no exista en la versión
      evaluada.
    </p>
  );
}

function SeccionCriterios({ evaluacion, contexto, alCambiar }: CabeceraProps) {
  const bloqueo = bloqueoAjuste(evaluacion);
  return (
    <section aria-labelledby="titulo-criterios" className="space-y-4">
      <h2 id="titulo-criterios" className="text-lg font-semibold">Criterios</h2>
      <AvisoVersionRubrica evaluacion={evaluacion} contexto={contexto} />
      {evaluacion.criterios.length === 0 ? (
        <EstadoVacio titulo="Sin criterios" mensaje="Esta evaluación no tiene resultados por criterio." />
      ) : (
        evaluacion.criterios.map((criterio) => {
          const criterioRubrica = buscarCriterioRubrica(contexto.rubrica?.contenido ?? null, criterio.criterio_id);
          return (
            <BloqueCriterio
              key={criterio.criterio_id}
              criterio={criterio}
              criterioRubrica={criterioRubrica}
              modoNivelIa="siempre"
              mostrarAjuste
            >
              {contexto.cargado && (
                <FormularioAjuste
                  evaluacionId={evaluacion.id}
                  criterio={criterio}
                  niveles={criterioRubrica?.niveles ?? null}
                  bloqueo={bloqueo}
                  alAjustar={alCambiar}
                />
              )}
            </BloqueCriterio>
          );
        })
      )}
    </section>
  );
}

function SeccionTraza({ evaluacion }: { evaluacion: Evaluacion }) {
  const cargar = useCallback(() => obtenerTraza(evaluacion.id), [evaluacion.id]);
  const { estado, recargar } = useCarga(cargar);
  return (
    <section aria-labelledby="titulo-traza" className="space-y-3">
      <h2 id="titulo-traza" className="text-lg font-semibold">Trazabilidad</h2>
      {estado.tipo === "cargando" && <Cargando texto="Cargando la traza…" />}
      {estado.tipo === "error" && (
        <MensajeError titulo="No se pudo cargar la traza" mensaje={estado.mensaje} alReintentar={recargar} />
      )}
      {estado.tipo === "listo" && <PanelTraza traza={estado.datos} evaluacion={evaluacion} />}
    </section>
  );
}

/** Huella de la evaluación: cambia con cada ajuste o cambio de estado y se usa como key para recargar la traza. */
function versionDe(evaluacion: Evaluacion): string {
  const niveles = evaluacion.criterios.map((c) => `${c.criterio_id}:${c.nivel_final}:${c.ajuste_docente ?? ""}`);
  return [evaluacion.estado, evaluacion.nota ?? "", ...niveles].join("|");
}

function ContenidoRevision({ evaluacion, fallos, alCambiar }: { evaluacion: Evaluacion; fallos: number; alCambiar: (e: Evaluacion) => void }) {
  const contexto = useContextoEvaluacion(evaluacion.laboratorio_id);

  return (
    <div className="space-y-8">
      {ENLACE_BANDEJA}
      <Cabecera evaluacion={evaluacion} contexto={contexto} alCambiar={alCambiar} />
      {estaProcesando(evaluacion) ? (
        <ProgresoEvaluacion fallos={fallos} />
      ) : evaluacion.estado === "error" ? (
        <ErrorEvaluacion detalle={evaluacion.error} esEstudiante={false} />
      ) : (
        <>
          <ResumenResultado evaluacion={evaluacion} />
          <SeccionCriterios evaluacion={evaluacion} contexto={contexto} alCambiar={alCambiar} />
          <section aria-labelledby="titulo-verificacion" className="space-y-3">
            <h2 id="titulo-verificacion" className="text-lg font-semibold">Verificación técnica del código</h2>
            <PanelVerificacion verificacion={evaluacion.verificacion} />
          </section>
        </>
      )}
      <SeccionTraza key={versionDe(evaluacion)} evaluacion={evaluacion} />
    </div>
  );
}

/** /docente/revision/[id]: revisión Human-in-the-Loop de una evaluación (RF-07). */
export function VistaRevision({ id }: { id: string }) {
  const idNumerico = idDesdeUrl(id);
  if (idNumerico === null) {
    return (
      <MensajeError titulo="Evaluación no encontrada" mensaje="La dirección no corresponde a ninguna evaluación.">
        <div className="mt-4">{ENLACE_BANDEJA}</div>
      </MensajeError>
    );
  }
  return <VistaRevisionValida id={idNumerico} />;
}

function VistaRevisionValida({ id }: { id: IdNumerico }) {
  const { estado, reintentar, reemplazar } = useSondeoEvaluacion(id);

  if (estado.tipo === "cargando") return <Cargando texto="Cargando la evaluación…" />;
  if (estado.tipo === "error") {
    return (
      <MensajeError titulo="No se pudo cargar la evaluación" mensaje={estado.mensaje} alReintentar={reintentar}>
        <div className="mt-4">{ENLACE_BANDEJA}</div>
      </MensajeError>
    );
  }
  return <ContenidoRevision evaluacion={estado.evaluacion} fallos={estado.fallos} alCambiar={reemplazar} />;
}
