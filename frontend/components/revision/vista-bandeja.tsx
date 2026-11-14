"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EstadoVacio, MensajeError } from "@/components/estados";
import { EtiquetaEstadoEvaluacion } from "@/components/evaluaciones/etiqueta-estado-evaluacion";
import { ESTADOS_EVALUACION, TEXTO_ESTADO_EVALUACION } from "@/components/evaluaciones/estado-evaluacion";
import { formatearFecha, formatearNota } from "@/components/portafolio/estado-entrega";
import {
  FILTROS_INICIALES,
  aParametros,
  cargarOpciones,
  esFiltroEstado,
  type FiltrosBandeja,
  type Opcion,
  type OpcionesFiltro,
} from "@/components/revision/datos-bandeja";
import { listarEvaluaciones } from "@/lib/api";
import { nombreVisible } from "@/lib/perfil";
import { rutaRevision } from "@/lib/rutas-evaluacion";
import type { EvaluacionResumen, ListadoEvaluaciones } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

const CLASE_SELECT = "h-9 w-full rounded-lg border bg-background px-3 text-sm sm:w-auto";

function textoNota(nota: number | null): string {
  return nota === null ? "—" : formatearNota(nota);
}

function enlace(fila: EvaluacionResumen): string {
  return rutaRevision(fila.id, { laboratorioId: fila.laboratorio.id, estudianteId: fila.estudiante.id });
}

function textoLaboratorio(fila: EvaluacionResumen): string {
  return `${fila.laboratorio.codigo} · ${fila.laboratorio.titulo}`;
}

function textoEstudiante(fila: EvaluacionResumen): string {
  return nombreVisible(fila.estudiante.nombre, "Estudiante sin nombre");
}

interface SelectorProps {
  id: string;
  etiqueta: string;
  valor: string;
  opciones: Opcion[];
  alCambiar: (valor: string) => void;
}

function Selector({ id, etiqueta, valor, opciones, alCambiar }: SelectorProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">{etiqueta}</label>
      <select id={id} value={valor} onChange={(e) => alCambiar(e.target.value)} className={CLASE_SELECT}>
        {opciones.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>{opcion.texto}</option>
        ))}
      </select>
    </div>
  );
}

const OPCIONES_ESTADO: Opcion[] = [
  ...ESTADOS_EVALUACION.map((estado) => ({ valor: estado, texto: TEXTO_ESTADO_EVALUACION[estado] })),
  { valor: "todas", texto: "Todas" },
];

interface FiltrosProps {
  filtros: FiltrosBandeja;
  opciones: OpcionesFiltro | null;
  alCambiar: (cambios: Partial<FiltrosBandeja>) => void;
}

/** Cambiar cualquier filtro vuelve a la primera página. */
function Filtros({ filtros, opciones, alCambiar }: FiltrosProps) {
  return (
    <fieldset className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
      <legend className="sr-only">Filtros de la bandeja</legend>
      <Selector id="filtro-estado" etiqueta="Estado" valor={filtros.estado} opciones={OPCIONES_ESTADO}
        alCambiar={(valor) => esFiltroEstado(valor) && alCambiar({ estado: valor, pagina: 0 })} />
      <Selector id="filtro-laboratorio" etiqueta="Laboratorio" valor={filtros.laboratorio}
        opciones={[{ valor: "", texto: "Todos" }, ...(opciones?.laboratorios ?? [])]}
        alCambiar={(valor) => alCambiar({ laboratorio: valor, pagina: 0 })} />
      {opciones?.estudiantes && (
        <Selector id="filtro-estudiante" etiqueta="Estudiante" valor={filtros.estudiante}
          opciones={[{ valor: "", texto: "Todos" }, ...opciones.estudiantes]}
          alCambiar={(valor) => alCambiar({ estudiante: valor, pagina: 0 })} />
      )}
    </fieldset>
  );
}

function TablaBandeja({ filas }: { filas: EvaluacionResumen[] }) {
  return (
    <div className="hidden overflow-x-auto rounded-xl border md:block">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Evaluaciones para revisar</caption>
        <thead className="bg-muted/60 text-xs uppercase text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3">Laboratorio</th>
            <th scope="col" className="px-4 py-3">Estudiante</th>
            <th scope="col" className="px-4 py-3">Generada</th>
            <th scope="col" className="px-4 py-3">Estado</th>
            <th scope="col" className="px-4 py-3 text-right">Nota</th>
            <th scope="col" className="px-4 py-3"><span className="sr-only">Acción</span></th>
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={fila.id} className="border-t">
              <td className="px-4 py-3 font-medium">{textoLaboratorio(fila)}</td>
              <td className="px-4 py-3">{textoEstudiante(fila)}</td>
              <td className="px-4 py-3 whitespace-nowrap">{formatearFecha(fila.creada_en)}</td>
              <td className="px-4 py-3"><EtiquetaEstadoEvaluacion estado={fila.estado} /></td>
              <td className="px-4 py-3 text-right font-mono">{textoNota(fila.nota)}</td>
              <td className="px-4 py-3 text-right">
                <Link href={enlace(fila)} className="font-medium underline underline-offset-4">
                  Revisar<span className="sr-only"> la evaluación de {textoEstudiante(fila)} en {textoLaboratorio(fila)}</span>
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TarjetasBandeja({ filas }: { filas: EvaluacionResumen[] }) {
  return (
    <ul className="space-y-3 md:hidden">
      {filas.map((fila) => (
        <li key={fila.id}>
          <Link href={enlace(fila)}
            className="block rounded-xl border bg-card p-4 hover:bg-muted/40 focus-visible:ring-3 focus-visible:ring-ring/50 outline-none">
            <p className="font-semibold">{textoLaboratorio(fila)}</p>
            <p className="text-sm">{textoEstudiante(fila)}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
              <EtiquetaEstadoEvaluacion estado={fila.estado} />
              <span>Nota: <strong>{textoNota(fila.nota)}</strong></span>
              <span className="text-muted-foreground">{formatearFecha(fila.creada_en)}</span>
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

function Paginacion({ listado, alCambiarPagina }: { listado: ListadoEvaluaciones; alCambiarPagina: (pagina: number) => void }) {
  const pagina = Math.floor(listado.offset / listado.limit);
  const paginas = Math.max(1, Math.ceil(listado.total / listado.limit));
  if (paginas <= 1) return null;
  return (
    <nav aria-label="Paginación de la bandeja" className="flex items-center justify-between gap-3">
      <Button variant="outline" size="sm" disabled={pagina === 0} onClick={() => alCambiarPagina(pagina - 1)}>
        <ChevronLeft aria-hidden="true" />
        Anterior
      </Button>
      <span className="text-sm text-muted-foreground">Página {pagina + 1} de {paginas}</span>
      <Button variant="outline" size="sm" disabled={pagina + 1 >= paginas} onClick={() => alCambiarPagina(pagina + 1)}>
        Siguiente
        <ChevronRight aria-hidden="true" />
      </Button>
    </nav>
  );
}

function ResultadoBandeja({ listado, filtros, alCambiarPagina }: { listado: ListadoEvaluaciones; filtros: FiltrosBandeja; alCambiarPagina: (p: number) => void }) {
  if (listado.items.length === 0) {
    const detalle = filtros.estado === "todas" ? "" : ` en estado “${TEXTO_ESTADO_EVALUACION[filtros.estado]}”`;
    return <EstadoVacio titulo="No hay evaluaciones para mostrar" mensaje={`No hay evaluaciones${detalle} con estos filtros.`} />;
  }
  const desde = listado.offset + 1;
  const hasta = listado.offset + listado.items.length;
  return (
    <>
      <p aria-live="polite" className="text-sm text-muted-foreground">
        {listado.total === 1 ? "1 evaluación" : `Mostrando ${desde}–${hasta} de ${listado.total} evaluaciones`}
      </p>
      <TablaBandeja filas={listado.items} />
      <TarjetasBandeja filas={listado.items} />
      <Paginacion listado={listado} alCambiarPagina={alCambiarPagina} />
    </>
  );
}

/** /docente/revision: bandeja de evaluaciones (GET /evaluaciones) con filtros y paginación. */
export function VistaBandeja() {
  const [filtros, setFiltros] = useState<FiltrosBandeja>(FILTROS_INICIALES);
  const opciones = useCarga(cargarOpciones);
  const cargar = useCallback(() => listarEvaluaciones(aParametros(filtros)), [filtros]);
  const { estado, recargar } = useCarga(cargar);
  const cambiar = (cambios: Partial<FiltrosBandeja>) => setFiltros((previos) => ({ ...previos, ...cambios }));

  return (
    <div className="mt-6 space-y-4">
      <Filtros filtros={filtros} opciones={opciones.estado.tipo === "listo" ? opciones.estado.datos : null} alCambiar={cambiar} />
      {estado.tipo === "cargando" && <EsqueletoBandeja />}
      {estado.tipo === "error" && (
        <MensajeError titulo="No se pudo cargar la bandeja" mensaje={estado.mensaje} alReintentar={recargar} />
      )}
      {estado.tipo === "listo" && (
        <ResultadoBandeja listado={estado.datos} filtros={filtros} alCambiarPagina={(pagina) => cambiar({ pagina })} />
      )}
    </div>
  );
}
