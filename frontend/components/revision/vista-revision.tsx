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
import {
  useContextoEvaluacion,
  useReferenciasEvaluacion,
  type ContextoEvaluacion,
  type Referencias,
} from "@/components/evaluaciones/use-contexto-evaluacion";
import { useSondeoEvaluacion } from "@/components/evaluaciones/use-sondeo-evaluacion";
import { AccionesRevision } from "@/components/revision/acciones-revision";
import { FormularioAjuste } from "@/components/revision/formulario-ajuste";
import { EditorRetroCriterio, EditorRetroGeneral } from "@/components/revision/formulario-retroalimentacion";
import { PanelTraza } from "@/components/revision/panel-traza";
import { PanelVerificacion } from "@/components/revision/panel-verificacion";
import { useNombreEstudiante } from "@/components/revision/use-nombre-estudiante";
import { obtenerTraza } from "@/lib/api";
import { nombreVisible } from "@/lib/perfil";
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

interface PropsRevision {
  evaluacion: Evaluacion;
  contexto: ContextoEvaluacion;
  referencias: Referencias;
  alCambiar: (evaluacion: Evaluacion) => void;
}

function Cabecera({ evaluacion, contexto, referencias, alCambiar }: PropsRevision) {
  const nombre = useNombreEstudiante(referencias.estudianteId);
  return (
    <header className="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          {contexto.laboratorio && <p className="font-mono text-xs text-muted-foreground">{contexto.laboratorio.codigo}</p>}
          <h1 className="text-2xl font-bold">{contexto.laboratorio?.titulo ?? `Revisión de la evaluación ${evaluacion.id}`}</h1>
          <p className="mt-1 text-sm">
            Estudiante: <span className="font-medium">{referencias.estudianteId ? nombreVisible(nombre, "Estudiante") : "No identificado"}</span>
          </p>
          <p className="text-sm text-muted-foreground">Generada el {formatearFechaHora(evaluacion.creada_en)}</p>
          {referencias.estudianteId && <EnlacesEstudiante estudianteId={referencias.estudianteId} />}
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

function bloqueoEdicion(evaluacion: Evaluacion): string | null {
  if (admiteAjustes(evaluacion)) return null;
  return `La evaluación está ${TEXTO_ESTADO_EVALUACION[evaluacion.estado].toLowerCase()}: ya no se pueden ajustar niveles ni editar textos.`;
}

function AvisoRubrica({ evaluacion, contexto, referencias }: Omit<PropsRevision, "alCambiar">) {
  if (referencias.laboratorioId === null) {
    return (
      <p role="note" className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
        No se pudo identificar el laboratorio (abre la evaluación desde la bandeja). Sin la rúbrica, los criterios se
        muestran por su código y no se pueden ajustar niveles; sí puedes editar los textos.
      </p>
    );
  }
  if (!contexto.cargado) return null;
  if (!contexto.rubrica) {
    return (
      <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
        No se pudo cargar la rúbrica del laboratorio{contexto.errorRubrica ? `: ${contexto.errorRubrica}` : "."} Sin ella no se
        pueden ajustar niveles.
      </p>
    );
  }
  if (evaluacion.rubrica_version === null || contexto.rubrica.version === evaluacion.rubrica_version) return null;
  return (
    <p role="note" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      La evaluación se hizo con la rúbrica v{evaluacion.rubrica_version}, pero la vigente es la v{contexto.rubrica.version}.
      Los niveles del selector son los de la versión vigente; el sistema rechazará un nivel que no exista en la versión
      evaluada.
    </p>
  );
}

function SeccionCriterios({ evaluacion, contexto, referencias, alCambiar }: PropsRevision) {
  const bloqueo = bloqueoEdicion(evaluacion);
  const puedeAjustar = referencias.laboratorioId !== null && contexto.cargado;
  return (
    <section aria-labelledby="titulo-criterios" className="space-y-4">
      <h2 id="titulo-criterios" className="text-lg font-semibold">Criterios</h2>
      <AvisoRubrica evaluacion={evaluacion} contexto={contexto} referencias={referencias} />
      {bloqueo && <p className="text-sm text-muted-foreground">{bloqueo}</p>}
      {evaluacion.criterios.length === 0 ? (
        <EstadoVacio titulo="Sin criterios" mensaje="Esta evaluación no tiene resultados por criterio." />
      ) : (
        evaluacion.criterios.map((criterio) => {
          const criterioRubrica = buscarCriterioRubrica(contexto.rubrica?.contenido ?? null, criterio.criterio_id);
          return (
            <BloqueCriterio key={criterio.criterio_id} criterio={criterio} criterioRubrica={criterioRubrica}
              modoNivelIa="siempre" mostrarAjuste>
              {!bloqueo && (
                <div className="space-y-3">
                  {puedeAjustar && (
                    <FormularioAjuste evaluacionId={evaluacion.id} criterio={criterio}
                      niveles={criterioRubrica?.niveles ?? null} bloqueo={null} alAjustar={alCambiar} />
                  )}
                  <EditorRetroCriterio evaluacionId={evaluacion.id} criterio={criterio} bloqueo={null} alGuardar={alCambiar} />
                </div>
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

/** Huella de la evaluación: cambia con cada ajuste, edición o cambio de estado y recarga la traza. */
function versionDe(evaluacion: Evaluacion): string {
  return JSON.stringify([evaluacion.estado, evaluacion.nota, evaluacion.criterios, evaluacion.retroalimentacion]);
}

function ContenidoRevision({ evaluacion, fallos, alCambiar }: { evaluacion: Evaluacion; fallos: number; alCambiar: (e: Evaluacion) => void }) {
  const referencias = useReferenciasEvaluacion(evaluacion);
  const contexto = useContextoEvaluacion(referencias.laboratorioId);
  const props = { evaluacion, contexto, referencias, alCambiar };

  return (
    <div className="space-y-8">
      {ENLACE_BANDEJA}
      <Cabecera {...props} />
      {estaProcesando(evaluacion) ? (
        <ProgresoEvaluacion fallos={fallos} />
      ) : evaluacion.estado === "error" ? (
        <ErrorEvaluacion detalle={evaluacion.error} esEstudiante={false} />
      ) : (
        <>
          <div className="space-y-3">
            <ResumenResultado evaluacion={evaluacion} />
            <EditorRetroGeneral key={versionDe(evaluacion)} evaluacion={evaluacion} bloqueo={bloqueoEdicion(evaluacion)}
              alGuardar={alCambiar} />
          </div>
          <SeccionCriterios {...props} />
          <section aria-labelledby="titulo-verificacion" className="space-y-3">
            <h2 id="titulo-verificacion" className="text-lg font-semibold">Verificación técnica del código</h2>
            <PanelVerificacion />
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
