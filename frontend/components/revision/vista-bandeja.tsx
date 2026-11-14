"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { EstadoVacio, MensajeError } from "@/components/estados";
import { EtiquetaEstadoEvaluacion } from "@/components/evaluaciones/etiqueta-estado-evaluacion";
import { ESTADOS_EVALUACION, TEXTO_ESTADO_EVALUACION } from "@/components/evaluaciones/estado-evaluacion";
import { formatearFecha, formatearNota } from "@/components/portafolio/estado-entrega";
import {
  FILTRO_POR_DEFECTO,
  cargarBandeja,
  filtrarBandeja,
  type FilaBandeja,
  type FiltroEstado,
} from "@/components/revision/datos-bandeja";
import { useCarga } from "@/lib/use-carga";

function rutaRevision(id: string): string {
  return `/docente/revision/${encodeURIComponent(id)}`;
}

function textoNota(nota: number | null): string {
  return nota === null ? "—" : formatearNota(nota);
}

function esFiltro(valor: string): valor is FiltroEstado {
  return valor === "todas" || ESTADOS_EVALUACION.some((estado) => estado === valor);
}

function SelectorEstado({ valor, alCambiar }: { valor: FiltroEstado; alCambiar: (valor: FiltroEstado) => void }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-2">
      <label htmlFor="filtro-estado" className="text-sm font-medium">
        Estado
      </label>
      <select
        id="filtro-estado"
        value={valor}
        onChange={(evento) => {
          if (esFiltro(evento.target.value)) alCambiar(evento.target.value);
        }}
        className="h-9 rounded-lg border bg-background px-3 text-sm"
      >
        {ESTADOS_EVALUACION.map((estado) => (
          <option key={estado} value={estado}>
            {TEXTO_ESTADO_EVALUACION[estado]}
          </option>
        ))}
        <option value="todas">Todas</option>
      </select>
    </div>
  );
}

function TablaBandeja({ filas }: { filas: FilaBandeja[] }) {
  return (
    <div className="hidden overflow-x-auto rounded-xl border md:block">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Evaluaciones para revisar</caption>
        <thead className="bg-muted/60 text-xs uppercase text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3">Laboratorio</th>
            <th scope="col" className="px-4 py-3">Estudiante</th>
            <th scope="col" className="px-4 py-3">Entregado</th>
            <th scope="col" className="px-4 py-3">Estado</th>
            <th scope="col" className="px-4 py-3 text-right">Nota</th>
            <th scope="col" className="px-4 py-3"><span className="sr-only">Acción</span></th>
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={fila.evaluacionId} className="border-t">
              <td className="px-4 py-3 font-medium">{fila.laboratorio}</td>
              <td className="px-4 py-3">{fila.estudiante}</td>
              <td className="px-4 py-3 whitespace-nowrap">{formatearFecha(fila.fecha)}</td>
              <td className="px-4 py-3"><EtiquetaEstadoEvaluacion estado={fila.estado} /></td>
              <td className="px-4 py-3 text-right font-mono">{textoNota(fila.nota)}</td>
              <td className="px-4 py-3 text-right">
                <Link href={rutaRevision(fila.evaluacionId)} className="font-medium underline underline-offset-4">
                  Revisar<span className="sr-only"> la evaluación de {fila.estudiante} en {fila.laboratorio}</span>
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TarjetasBandeja({ filas }: { filas: FilaBandeja[] }) {
  return (
    <ul className="space-y-3 md:hidden">
      {filas.map((fila) => (
        <li key={fila.evaluacionId}>
          <Link
            href={rutaRevision(fila.evaluacionId)}
            className="block rounded-xl border bg-card p-4 hover:bg-muted/40 focus-visible:ring-3 focus-visible:ring-ring/50 outline-none"
          >
            <p className="font-semibold">{fila.laboratorio}</p>
            <p className="text-sm">{fila.estudiante}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
              <EtiquetaEstadoEvaluacion estado={fila.estado} />
              <span>Nota: <strong>{textoNota(fila.nota)}</strong></span>
              <span className="text-muted-foreground">{formatearFecha(fila.fecha)}</span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function EsqueletoBandeja() {
  return (
    <div role="status" className="mt-6 space-y-3">
      {[0, 1, 2].map((fila) => (
        <div key={fila} className="h-14 animate-pulse rounded-xl bg-muted" />
      ))}
      <span className="sr-only">Cargando evaluaciones…</span>
    </div>
  );
}

/** /docente/revision: bandeja de evaluaciones filtrada por estado (por defecto, borradores). */
export function VistaBandeja() {
  const [filtro, setFiltro] = useState<FiltroEstado>(FILTRO_POR_DEFECTO);
  const cargar = useCallback(() => cargarBandeja(), []);
  const { estado, recargar } = useCarga(cargar);

  return (
    <div className="mt-6 space-y-4">
      <SelectorEstado valor={filtro} alCambiar={setFiltro} />
      {estado.tipo === "cargando" && <EsqueletoBandeja />}
      {estado.tipo === "error" && (
        <MensajeError titulo="No se pudo cargar la bandeja" mensaje={estado.mensaje} alReintentar={recargar} />
      )}
      {estado.tipo === "listo" && <ResultadoBandeja filas={filtrarBandeja(estado.datos, filtro)} filtro={filtro} />}
    </div>
  );
}

function ResultadoBandeja({ filas, filtro }: { filas: FilaBandeja[]; filtro: FiltroEstado }) {
  if (filas.length === 0) {
    const detalle = filtro === "todas" ? "" : ` en estado “${TEXTO_ESTADO_EVALUACION[filtro]}”`;
    return (
      <EstadoVacio
        titulo="No hay evaluaciones para mostrar"
        mensaje={`No hay evaluaciones${detalle}. Prueba con otro filtro.`}
      />
    );
  }
  return (
    <>
      <p aria-live="polite" className="text-sm text-muted-foreground">
        {filas.length === 1 ? "1 evaluación" : `${filas.length} evaluaciones`}
      </p>
      <TablaBandeja filas={filas} />
      <TarjetasBandeja filas={filas} />
    </>
  );
}
