"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MensajeError } from "@/components/estados";
import { LIMITE_MAXIMO_LISTADO, listarEstudiantes } from "@/lib/api";
import { nombreVisible } from "@/lib/perfil";
import type { EstudianteListado, ListadoEstudiantes } from "@/lib/tipos";
import { useCarga, type EstadoCarga } from "@/lib/use-carga";

/** Estudiantes por página en el selector del docente. */
export const ESTUDIANTES_POR_PAGINA = 10;

/** Una página de GET /estudiantes (docente/admin). */
function usePaginaEstudiantes(pagina: number, limite: number) {
  const cargar = useCallback(() => listarEstudiantes(limite, pagina * limite), [pagina, limite]);
  return useCarga(cargar);
}

/** Lista para buscar el nombre de un estudiante (primera página de hasta 100). */
export function useListaEstudiantes(): { estado: EstadoCarga<ListadoEstudiantes> } {
  const { estado } = usePaginaEstudiantes(0, LIMITE_MAXIMO_LISTADO);
  return { estado };
}

/** Nombre de un estudiante según la lista del docente (null mientras carga o si no aparece). */
export function nombreEnLista(estado: EstadoCarga<ListadoEstudiantes>, estudianteId: string): string | null {
  if (estado.tipo !== "listo") return null;
  return estado.datos.items.find((e) => e.id === estudianteId)?.nombre ?? null;
}

function textoOpcion(estudiante: EstudianteListado): string {
  const evaluados = estudiante.laboratorios_evaluados;
  const detalle = evaluados === 1 ? "1 laboratorio evaluado" : `${evaluados} laboratorios evaluados`;
  return `${nombreVisible(estudiante.nombre, "Estudiante sin nombre")} · ${detalle}`;
}

interface PaginacionProps {
  listado: ListadoEstudiantes;
  pagina: number;
  alCambiar: (pagina: number) => void;
}

function PaginacionEstudiantes({ listado, pagina, alCambiar }: PaginacionProps) {
  const paginas = Math.max(1, Math.ceil(listado.total / listado.limit));
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <Button type="button" variant="outline" size="sm" disabled={pagina === 0} onClick={() => alCambiar(pagina - 1)}>
        <ChevronLeft aria-hidden="true" />
        Anterior
      </Button>
      <span aria-live="polite" className="text-muted-foreground">
        Página {pagina + 1} de {paginas} · {listado.total === 1 ? "1 estudiante" : `${listado.total} estudiantes`}
      </span>
      <Button type="button" variant="outline" size="sm" disabled={pagina + 1 >= paginas} onClick={() => alCambiar(pagina + 1)}>
        Siguiente
        <ChevronRight aria-hidden="true" />
      </Button>
    </div>
  );
}

interface SelectorEstudianteProps {
  /** Pantalla a la que lleva: /informe/{id} o /mapa/{id}. */
  destino: "informe" | "mapa";
  /** Estudiante que se está viendo (para preseleccionarlo si está en la página actual). */
  actual?: string;
}

/** Selector del estudiante para docente/admin (RF-08/RF-09), paginado con GET /estudiantes. */
export function SelectorEstudiante({ destino, actual }: SelectorEstudianteProps) {
  const router = useRouter();
  const [pagina, setPagina] = useState(0);
  const { estado, recargar } = usePaginaEstudiantes(pagina, ESTUDIANTES_POR_PAGINA);

  if (estado.tipo === "cargando") {
    return (
      <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground print:hidden">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        Cargando la lista de estudiantes…
      </p>
    );
  }
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar la lista de estudiantes" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  const listado = estado.datos;
  if (listado.total === 0) {
    return <p className="text-sm text-muted-foreground print:hidden">Aún no hay estudiantes registrados.</p>;
  }
  const actualEnPagina = actual !== undefined && listado.items.some((e) => e.id === actual);

  return (
    <div className="space-y-2 print:hidden sm:max-w-xl">
      <div className="flex flex-col gap-1">
        <label htmlFor="selector-estudiante" className="text-sm font-medium">Estudiante</label>
        <select
          id="selector-estudiante"
          value={actualEnPagina ? actual : ""}
          onChange={(e) => e.target.value && router.push(`/${destino}/${encodeURIComponent(e.target.value)}`)}
          className="h-9 w-full rounded-lg border bg-background px-3 text-sm"
        >
          <option value="" disabled>Elige un estudiante…</option>
          {listado.items.map((estudiante) => (
            <option key={estudiante.id} value={estudiante.id}>{textoOpcion(estudiante)}</option>
          ))}
        </select>
      </div>
      <PaginacionEstudiantes listado={listado} pagina={pagina} alCambiar={setPagina} />
    </div>
  );
}

/** Pantalla inicial de /informe o /mapa para docente/admin: solo el selector. */
export function ElegirEstudiante({ destino }: { destino: "informe" | "mapa" }) {
  const titulo = destino === "informe" ? "Informe integral del aprendizaje" : "Mapa mental de competencias";
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">{titulo}</h1>
      <p className="text-sm text-muted-foreground">
        Elige un estudiante para ver su {destino === "informe" ? "informe" : "mapa mental"}. Solo se incluyen
        evaluaciones publicadas.
      </p>
      <SelectorEstudiante destino={destino} />
    </section>
  );
}

/** Avisos que acompañan al informe o al mapa (campo `avisos` del backend). */
export function ListaAvisos({ avisos }: { avisos: string[] }) {
  if (avisos.length === 0) return null;
  return (
    <div role="note" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <p className="font-medium">Avisos</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5">
        {avisos.map((aviso, indice) => (
          <li key={`${indice}-${aviso}`}>{aviso}</li>
        ))}
      </ul>
    </div>
  );
}
