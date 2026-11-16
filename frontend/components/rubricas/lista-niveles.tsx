"use client";

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CLASE_CONTROL } from "@/components/docente/campo";
import {
  mover,
  nuevoNivel,
  parsearNumero,
  quitar,
  reemplazar,
  type NivelEditor,
} from "@/components/rubricas/modelo-editor";

interface ListaNivelesProps {
  /** Prefijo único para los ids de los campos (la clave del criterio). */
  prefijo: string;
  nombreCriterio: string;
  niveles: NivelEditor[];
  deshabilitado: boolean;
  alCambiar: (niveles: NivelEditor[]) => void;
}

/** Niveles de desempeño de un criterio: nombre, puntaje y descriptor. En móvil, cada nivel es un bloque apilado. */
export function ListaNiveles({ prefijo, nombreCriterio, niveles, deshabilitado, alCambiar }: ListaNivelesProps) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">Niveles de desempeño (del mejor al peor puntaje)</legend>
      {niveles.length === 0 && <p className="text-sm text-muted-foreground">Este criterio aún no tiene niveles.</p>}
      <ol className="space-y-2">
        {niveles.map((nivel, indice) => (
          <FilaNivel
            key={nivel.clave}
            id={`${prefijo}-${nivel.clave}`}
            nivel={nivel}
            posicion={indice + 1}
            total={niveles.length}
            nombreCriterio={nombreCriterio}
            deshabilitado={deshabilitado}
            alCambiar={(cambios) => alCambiar(reemplazar(niveles, indice, { ...nivel, ...cambios }))}
            alMover={(delta) => alCambiar(mover(niveles, indice, delta))}
            alEliminar={() => alCambiar(quitar(niveles, indice))}
          />
        ))}
      </ol>
      <Button type="button" variant="outline" size="sm" disabled={deshabilitado} onClick={() => alCambiar([...niveles, nuevoNivel()])}>
        <Plus aria-hidden="true" />
        Agregar nivel
      </Button>
    </fieldset>
  );
}

interface FilaNivelProps {
  id: string;
  nivel: NivelEditor;
  posicion: number;
  total: number;
  nombreCriterio: string;
  deshabilitado: boolean;
  alCambiar: (cambios: Partial<NivelEditor>) => void;
  alMover: (delta: number) => void;
  alEliminar: () => void;
}

function FilaNivel({ id, nivel, posicion, total, nombreCriterio, deshabilitado, alCambiar, alMover, alEliminar }: FilaNivelProps) {
  const descripcion = `nivel ${posicion} de ${nombreCriterio.trim() || "este criterio"}`;
  return (
    <li className="grid gap-2 rounded-lg border bg-muted/30 p-3 md:grid-cols-[minmax(0,10rem)_6rem_minmax(0,1fr)_auto] md:items-start">
      <div className="space-y-1">
        <label htmlFor={`${id}-nombre`} className="text-xs font-medium">Nombre</label>
        <input id={`${id}-nombre`} value={nivel.nombre} disabled={deshabilitado} placeholder="Excelente"
          aria-invalid={nivel.nombre.trim() === "" || undefined} className={CLASE_CONTROL}
          onChange={(e) => alCambiar({ nombre: e.target.value })} />
      </div>
      <div className="space-y-1">
        <label htmlFor={`${id}-puntaje`} className="text-xs font-medium">Puntaje</label>
        <input id={`${id}-puntaje`} type="number" step="any" inputMode="decimal" value={nivel.puntaje ?? ""}
          disabled={deshabilitado} aria-invalid={nivel.puntaje === null || undefined} className={CLASE_CONTROL}
          onChange={(e) => alCambiar({ puntaje: parsearNumero(e.target.value) })} />
      </div>
      <div className="space-y-1">
        <label htmlFor={`${id}-descriptor`} className="text-xs font-medium">Descriptor</label>
        <textarea id={`${id}-descriptor`} rows={2} value={nivel.descriptor} disabled={deshabilitado}
          aria-invalid={nivel.descriptor.trim() === "" || undefined} className={CLASE_CONTROL}
          onChange={(e) => alCambiar({ descriptor: e.target.value })} />
      </div>
      <div className="flex gap-1 md:flex-col md:pt-5">
        <Button type="button" variant="ghost" size="icon-sm" disabled={deshabilitado || posicion === 1}
          aria-label={`Subir ${descripcion}`} onClick={() => alMover(-1)}>
          <ArrowUp aria-hidden="true" />
        </Button>
        <Button type="button" variant="ghost" size="icon-sm" disabled={deshabilitado || posicion === total}
          aria-label={`Bajar ${descripcion}`} onClick={() => alMover(1)}>
          <ArrowDown aria-hidden="true" />
        </Button>
        <Button type="button" variant="ghost" size="icon-sm" disabled={deshabilitado}
          aria-label={`Eliminar ${descripcion}`} onClick={alEliminar}>
          <Trash2 aria-hidden="true" className="text-destructive" />
        </Button>
      </div>
    </li>
  );
}
