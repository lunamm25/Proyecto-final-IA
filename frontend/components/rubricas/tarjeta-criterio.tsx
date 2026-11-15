"use client";

import { AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Campo, CLASE_CONTROL } from "@/components/docente/campo";
import { ListaNiveles } from "@/components/rubricas/lista-niveles";
import { parsearNumero, type CriterioEditor } from "@/components/rubricas/modelo-editor";
import type { Inconsistencia, TipoInconsistencia } from "@/lib/tipos";

interface TarjetaCriterioProps {
  criterio: CriterioEditor;
  posicion: number;
  total: number;
  inconsistencias: Inconsistencia[];
  deshabilitado: boolean;
  alCambiar: (cambios: Partial<CriterioEditor>) => void;
  alMover: (delta: number) => void;
  alEliminar: () => void;
}

function tiene(inconsistencias: Inconsistencia[], tipo: TipoInconsistencia): boolean {
  return inconsistencias.some((i) => i.tipo === tipo);
}

function ProblemasCriterio({ id, inconsistencias }: { id: string; inconsistencias: Inconsistencia[] }) {
  if (inconsistencias.length === 0) {
    return (
      <p id={id} className="flex items-center gap-1 text-sm text-emerald-700">
        <CheckCircle2 className="size-4" aria-hidden="true" />
        Sin inconsistencias
      </p>
    );
  }
  return (
    <div id={id} className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <p className="flex items-center gap-1 font-medium">
        <AlertTriangle className="size-4" aria-hidden="true" />
        {inconsistencias.length === 1 ? "1 inconsistencia" : `${inconsistencias.length} inconsistencias`}
      </p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5">
        {inconsistencias.map((inc, i) => (
          <li key={`${inc.tipo}-${i}`}>{inc.mensaje}</li>
        ))}
      </ul>
    </div>
  );
}

/** Tarjeta de un criterio: datos básicos, niveles, inconsistencias propias y acciones de orden/eliminación. */
export function TarjetaCriterio(props: TarjetaCriterioProps) {
  const { criterio, posicion, total, inconsistencias, deshabilitado, alCambiar, alMover, alEliminar } = props;
  const id = `criterio-${criterio.clave}`;
  const nombre = criterio.nombre.trim() || `criterio ${posicion}`;
  const duplicado = tiene(inconsistencias, "criterio_duplicado");
  return (
    <li aria-labelledby={`${id}-titulo`} className="space-y-4 rounded-xl border p-4 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`${id}-titulo`} className="font-semibold">
          Criterio {posicion}
          {criterio.nombre.trim() && <span className="font-normal text-muted-foreground"> · {criterio.nombre.trim()}</span>}
        </h3>
        <div className="flex gap-1">
          <Button type="button" variant="ghost" size="icon-sm" disabled={deshabilitado || posicion === 1}
            aria-label={`Subir ${nombre}`} onClick={() => alMover(-1)}>
            <ArrowUp aria-hidden="true" />
          </Button>
          <Button type="button" variant="ghost" size="icon-sm" disabled={deshabilitado || posicion === total}
            aria-label={`Bajar ${nombre}`} onClick={() => alMover(1)}>
            <ArrowDown aria-hidden="true" />
          </Button>
          <Button type="button" variant="destructive" size="sm" disabled={deshabilitado} onClick={alEliminar}
            aria-label={`Eliminar ${nombre}`}>
            <Trash2 aria-hidden="true" />
            <span className="hidden sm:inline">Eliminar</span>
          </Button>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[8rem_minmax(0,1fr)_minmax(0,1fr)_8rem]">
        <Campo id={`${id}-id`} etiqueta="Id" obligatorio error={criterio.id.trim() === "" ? "Obligatorio." : undefined}>
          {(a11y) => (
            <input {...a11y} value={criterio.id} disabled={deshabilitado} className={CLASE_CONTROL}
              aria-invalid={a11y["aria-invalid"] ?? (duplicado || undefined)}
              onChange={(e) => alCambiar({ id: e.target.value })} />
          )}
        </Campo>
        <Campo id={`${id}-nombre`} etiqueta="Nombre" obligatorio>
          {(a11y) => (
            <input {...a11y} value={criterio.nombre} disabled={deshabilitado} className={CLASE_CONTROL}
              aria-invalid={criterio.nombre.trim() === "" || duplicado || undefined}
              aria-describedby={`${id}-problemas`} onChange={(e) => alCambiar({ nombre: e.target.value })} />
          )}
        </Campo>
        <Campo id={`${id}-competencia`} etiqueta="Competencia" obligatorio>
          {(a11y) => (
            <input {...a11y} value={criterio.competencia} disabled={deshabilitado} className={CLASE_CONTROL}
              aria-invalid={tiene(inconsistencias, "competencia_vacia") || undefined}
              aria-describedby={`${id}-problemas`} onChange={(e) => alCambiar({ competencia: e.target.value })} />
          )}
        </Campo>
        <Campo id={`${id}-ponderacion`} etiqueta="Ponderación (%)" obligatorio>
          {(a11y) => (
            <input {...a11y} type="number" min={0} max={100} step="any" inputMode="decimal"
              value={criterio.ponderacion ?? ""} disabled={deshabilitado} className={CLASE_CONTROL}
              aria-invalid={criterio.ponderacion === null || criterio.ponderacion <= 0 || undefined}
              aria-describedby={`${id}-problemas`}
              onChange={(e) => alCambiar({ ponderacion: parsearNumero(e.target.value) })} />
          )}
        </Campo>
      </div>
      <ListaNiveles prefijo={id} nombreCriterio={criterio.nombre} niveles={criterio.niveles} deshabilitado={deshabilitado}
        alCambiar={(niveles) => alCambiar({ niveles })} />
      <ProblemasCriterio id={`${id}-problemas`} inconsistencias={inconsistencias} />
    </li>
  );
}
