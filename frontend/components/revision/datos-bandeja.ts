import { buscarLaboratorio } from "@/components/evaluaciones/use-contexto-evaluacion";
import { listarCohortes, listarEntregas, listarUsuarios } from "@/lib/api";
import type { EstadoEvaluacion, Usuario } from "@/lib/tipos";

export type FiltroEstado = EstadoEvaluacion | "todas";

export const FILTRO_POR_DEFECTO: FiltroEstado = "borrador";

export interface FilaBandeja {
  evaluacionId: string;
  estado: EstadoEvaluacion;
  /** Nota que envía el backend en el resumen de la entrega. */
  nota: number | null;
  laboratorio: string;
  estudiante: string;
  fecha: string;
}

/** Los nombres son opcionales: si /usuarios falla, se muestra el id del estudiante (nunca el correo). */
async function nombresDeEstudiantes(): Promise<Map<string, string>> {
  try {
    const usuarios: Usuario[] = await listarUsuarios();
    return new Map(usuarios.flatMap((u) => (u.nombre ? [[u.id, u.nombre] as const] : [])));
  } catch {
    return new Map();
  }
}

/**
 * El contrato §11 no tiene un listado de evaluaciones: se arma con GET /entregas (sin estudiante_id, docente),
 * que trae el resumen {id, estado, nota} de la evaluación de cada entrega.
 */
export async function cargarBandeja(): Promise<FilaBandeja[]> {
  const [entregas, cohortes, nombres] = await Promise.all([listarEntregas(), listarCohortes(), nombresDeEstudiantes()]);
  return entregas
    .flatMap((entrega) => {
      if (!entrega.evaluacion) return [];
      const laboratorio = buscarLaboratorio(cohortes, entrega.laboratorio_id);
      return [
        {
          evaluacionId: entrega.evaluacion.id,
          estado: entrega.evaluacion.estado,
          nota: entrega.evaluacion.nota,
          laboratorio: laboratorio ? `${laboratorio.codigo} · ${laboratorio.titulo}` : entrega.laboratorio_id,
          estudiante: nombres.get(entrega.estudiante_id) ?? `Estudiante ${entrega.estudiante_id}`,
          fecha: entrega.creada_en,
        },
      ];
    })
    .sort((a, b) => b.fecha.localeCompare(a.fecha));
}

export function filtrarBandeja(filas: FilaBandeja[], filtro: FiltroEstado): FilaBandeja[] {
  return filtro === "todas" ? filas : filas.filter((fila) => fila.estado === filtro);
}
