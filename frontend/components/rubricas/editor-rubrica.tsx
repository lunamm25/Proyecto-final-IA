"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, Plus, Server, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Aviso, type DatosAviso } from "@/components/docente/aviso";
import { Campo, CLASE_CONTROL } from "@/components/docente/campo";
import { editorARubrica, rubricaVacia, rubricaAEditor, tieneContenido, tieneNumerosVacios } from "@/components/rubricas/modelo-editor";
import { ResumenInconsistencias } from "@/components/rubricas/resumen-inconsistencias";
import { SubirRubrica } from "@/components/rubricas/subir-rubrica";
import { SumaPonderaciones } from "@/components/rubricas/suma-ponderaciones";
import { TarjetaCriterio } from "@/components/rubricas/tarjeta-criterio";
import { useAvisoSalida } from "@/components/rubricas/use-aviso-salida";
import { useEditorRubrica } from "@/components/rubricas/use-editor-rubrica";
import { ErrorApi, guardarVersionRubrica, mensajeDeError, validarRubrica } from "@/lib/api";
import { agruparInconsistencias, camposObligatoriosVacios, sumaPonderaciones } from "@/lib/inconsistencias-rubrica";
import type { Laboratorio, RubricaVersion } from "@/lib/tipos";

type Ocupado = "extrayendo" | "validando" | "guardando" | null;

interface EditorRubricaProps {
  laboratorio: Laboratorio;
  vigente: RubricaVersion | null;
  alGuardar: (version: RubricaVersion) => void;
}

function mensajeConfirmacion(siguiente: number): string {
  return (
    `Se creará la versión ${siguiente} de la rúbrica y quedará aprobada como vigente.\n\n` +
    "Las versiones aprobadas son inmutables: si después la editas, se creará otra versión. " +
    "Las entregas existentes conservan la versión con la que se entregaron.\n\n¿Deseas continuar?"
  );
}

/** Editor de rúbrica con inconsistencias en vivo (RF-03 CA3), aprobación bloqueada si hay problemas (CA4) y versionado (CA5). */
export function EditorRubrica({ laboratorio, vigente, alGuardar }: EditorRubricaProps) {
  const editor = useEditorRubrica(() => (vigente ? rubricaAEditor(vigente.contenido) : rubricaVacia(laboratorio.titulo)));
  const { borrador, sucio, servidor } = editor;
  const [ocupado, setOcupado] = useState<Ocupado>(null);
  const [aviso, setAviso] = useState<DatosAviso | null>(null);
  useAvisoSalida(sucio);

  const { generales, porCriterio } = agruparInconsistencias(borrador);
  const inconsistencias = [...generales, ...porCriterio.flat()];
  const camposVacios = camposObligatoriosVacios(borrador);
  // Si la extracción llegó con valida: false, no se puede guardar hasta que el servidor valide la rúbrica corregida.
  const bloqueado = inconsistencias.length > 0 || camposVacios.length > 0 || editor.revisionPendiente;
  const siguiente = (vigente?.version ?? 0) + 1;

  async function validarEnServidor() {
    if (tieneNumerosVacios(borrador)) {
      setAviso({ tipo: "error", mensaje: "Completa los puntajes y ponderaciones vacíos antes de validar con el servidor." });
      return;
    }
    setOcupado("validando");
    setAviso(null);
    try {
      const resultado = await validarRubrica(editorARubrica(borrador));
      editor.setServidor({ origen: "validacion", inconsistencias: resultado.inconsistencias });
      if (resultado.valida) editor.marcarValidadaPorServidor();
    } catch (causa) {
      setAviso({ tipo: "error", mensaje: mensajeDeError(causa) });
    } finally {
      setOcupado(null);
    }
  }

  async function guardar() {
    if (bloqueado || !window.confirm(mensajeConfirmacion(siguiente))) return;
    setOcupado("guardando");
    setAviso(null);
    try {
      const nueva = await guardarVersionRubrica(laboratorio.id, editorARubrica(borrador));
      editor.marcarGuardado(nueva.contenido);
      alGuardar(nueva);
      setAviso({ tipo: "exito", mensaje: `Rúbrica guardada y aprobada como versión ${nueva.version}.` });
    } catch (causa) {
      if (causa instanceof ErrorApi && causa.inconsistencias.length > 0) {
        editor.setServidor({ origen: "guardado", inconsistencias: causa.inconsistencias });
      }
      setAviso({ tipo: "error", mensaje: mensajeDeError(causa) });
    } finally {
      setOcupado(null);
    }
  }

  const deshabilitado = ocupado !== null;

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="space-y-6">
        <SubirRubrica
          labId={laboratorio.id}
          hayContenido={tieneContenido(borrador)}
          deshabilitado={deshabilitado}
          alCambiarOcupado={(activo) => setOcupado(activo ? "extrayendo" : null)}
          alExtraer={(resultado) => {
            editor.cargarExtraida(
              resultado.rubrica,
              { origen: "extraccion", inconsistencias: resultado.inconsistencias },
              resultado.valida,
            );
            setAviso(
              resultado.valida
                ? { tipo: "info", mensaje: "Rúbrica extraída y válida según el servidor. Revísala antes de aprobarla." }
                : null,
            );
          }}
        />
        <section aria-labelledby="titulo-editor" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="titulo-editor" className="text-xl font-semibold">
              Editor de la rúbrica
            </h2>
            <SumaPonderaciones suma={sumaPonderaciones(borrador)} />
          </div>
          <Campo id="rubrica-titulo" etiqueta="Título de la rúbrica" obligatorio
            error={borrador.titulo.trim() === "" ? "El título es obligatorio." : undefined}>
            {(a11y) => (
              <input {...a11y} value={borrador.titulo} disabled={deshabilitado} className={CLASE_CONTROL}
                onChange={(e) => editor.cambiarTitulo(e.target.value)} />
            )}
          </Campo>
          <ListaCriterios editor={editor} porCriterio={porCriterio} deshabilitado={deshabilitado} />
        </section>
      </div>
      <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
        {editor.revisionPendiente && <AvisoExtraccionInvalida />}
        <ResumenInconsistencias inconsistencias={inconsistencias} camposVacios={camposVacios} servidor={servidor} />
        {aviso && <Aviso {...aviso} />}
        <AccionesRubrica
          ocupado={ocupado}
          bloqueado={bloqueado}
          revisionPendiente={editor.revisionPendiente}
          sucio={sucio}
          siguiente={siguiente}
          alValidar={() => void validarEnServidor()}
          alGuardar={() => void guardar()}
        />
      </aside>
    </div>
  );
}

interface ListaCriteriosProps {
  editor: ReturnType<typeof useEditorRubrica>;
  porCriterio: ReturnType<typeof agruparInconsistencias>["porCriterio"];
  deshabilitado: boolean;
}

function ListaCriterios({ editor, porCriterio, deshabilitado }: ListaCriteriosProps) {
  const criterios = editor.borrador.criterios;
  function eliminar(indice: number) {
    const nombre = criterios[indice].nombre.trim() || `el criterio ${indice + 1}`;
    if (window.confirm(`¿Eliminar ${nombre} y todos sus niveles?`)) editor.eliminarCriterio(indice);
  }
  return (
    <>
      {criterios.length === 0 ? (
        <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          Aún no hay criterios. Agrega uno o sube un archivo para extraer la rúbrica con IA.
        </p>
      ) : (
        <ol className="space-y-4" aria-label="Criterios de la rúbrica">
          {criterios.map((criterio, indice) => (
            <TarjetaCriterio key={criterio.clave} criterio={criterio} posicion={indice + 1} total={criterios.length}
              inconsistencias={porCriterio[indice] ?? []} deshabilitado={deshabilitado}
              alCambiar={(cambios) => editor.cambiarCriterio(indice, cambios)}
              alMover={(delta) => editor.moverCriterio(indice, delta)} alEliminar={() => eliminar(indice)} />
          ))}
        </ol>
      )}
      <Button type="button" variant="outline" onClick={editor.agregarCriterio} disabled={deshabilitado}>
        <Plus aria-hidden="true" />
        Agregar criterio
      </Button>
    </>
  );
}

interface AccionesRubricaProps {
  ocupado: Ocupado;
  bloqueado: boolean;
  revisionPendiente: boolean;
  sucio: boolean;
  siguiente: number;
  alValidar: () => void;
  alGuardar: () => void;
}

/** La IA propuso una rúbrica que el validador del backend marcó como no válida (valida: false). */
function AvisoExtraccionInvalida() {
  return (
    <div role="alert" className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-1">
        <p className="font-medium">La rúbrica extraída no es válida todavía.</p>
        <p>
          Corrige las inconsistencias que reportó el servidor y pulsa «Validar con el servidor». Cuando el servidor la
          dé por válida, podrás guardarla.
        </p>
      </div>
    </div>
  );
}

function textoAyudaGuardar(bloqueado: boolean, revisionPendiente: boolean, siguiente: number): string {
  if (revisionPendiente) return "La rúbrica extraída tiene inconsistencias: corrígelas y valídala con el servidor antes de guardar.";
  if (bloqueado) return "Corrige todos los problemas de la revisión para poder aprobar.";
  return `Se creará la versión ${siguiente}, inmutable. Las entregas existentes conservan su versión.`;
}

function AccionesRubrica({ ocupado, bloqueado, revisionPendiente, sucio, siguiente, alValidar, alGuardar }: AccionesRubricaProps) {
  return (
    <div className="space-y-2 rounded-xl border p-4">
      {sucio && <p className="text-sm font-medium text-amber-700">Tienes cambios sin guardar.</p>}
      <Button type="button" variant="outline" className="w-full" disabled={ocupado !== null} onClick={alValidar}>
        {ocupado === "validando" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Server aria-hidden="true" />}
        {ocupado === "validando" ? "Validando…" : "Validar con el servidor"}
      </Button>
      <Button type="button" className="w-full" disabled={ocupado !== null || bloqueado} onClick={alGuardar}
        aria-describedby="ayuda-guardar">
        {ocupado === "guardando" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}
        {ocupado === "guardando" ? "Guardando…" : "Guardar y aprobar nueva versión"}
      </Button>
      <p id="ayuda-guardar" className="text-xs text-muted-foreground">
        {textoAyudaGuardar(bloqueado, revisionPendiente, siguiente)}
      </p>
    </div>
  );
}
