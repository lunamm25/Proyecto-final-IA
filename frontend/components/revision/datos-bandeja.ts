// Bandeja de revisión: GET /api/evaluaciones con filtros y paginación (limit/offset). Los filtros los aplica el backend.
import { ESTADOS_EVALUACION } from "@/components/evaluaciones/estado-evaluacion";
import { LIMITE_EVALUACIONES_POR_DEFECTO, LIMITE_MAXIMO_LISTADO, listarCohortes, listarEstudiantes } from "@/lib/api";
import { nombreVisible } from "@/lib/perfil";
import { idDesdeUrl, type EstadoEvaluacion, type FiltrosEvaluaciones } from "@/lib/tipos";

export type FiltroEstado = EstadoEvaluacion | "todas";

export const FILTRO_POR_DEFECTO: FiltroEstado = "borrador";

export const TAMANO_PAGINA = LIMITE_EVALUACIONES_POR_DEFECTO;

/** Valores del formulario de filtros ("" = sin filtrar). */
export interface FiltrosBandeja {
  estado: FiltroEstado;
  laboratorio: string;
  estudiante: string;
  pagina: number;
}

export const FILTROS_INICIALES: FiltrosBandeja = { estado: FILTRO_POR_DEFECTO, laboratorio: "", estudiante: "", pagina: 0 };

export function esFiltroEstado(valor: string): valor is FiltroEstado {
  return valor === "todas" || ESTADOS_EVALUACION.some((estado) => estado === valor);
}

/** Convierte los filtros del formulario en los parámetros de GET /evaluaciones. */
export function aParametros(filtros: FiltrosBandeja): FiltrosEvaluaciones {
  const laboratorio = idDesdeUrl(filtros.laboratorio);
  return {
    ...(filtros.estado !== "todas" ? { estado: filtros.estado } : {}),
    ...(laboratorio !== null ? { laboratorio_id: laboratorio } : {}),
    ...(filtros.estudiante ? { estudiante_id: filtros.estudiante } : {}),
    limit: TAMANO_PAGINA,
    offset: filtros.pagina * TAMANO_PAGINA,
  };
}

export interface Opcion {
  valor: string;
  texto: string;
}

export interface OpcionesFiltro {
  laboratorios: Opcion[];
  /** null = no se pudo cargar la lista de estudiantes (el filtro se oculta). */
  estudiantes: Opcion[] | null;
}

/** Opciones de los selectores: laboratorios de GET /cohortes y estudiantes de GET /estudiantes. */
export async function cargarOpciones(): Promise<OpcionesFiltro> {
  const [cohortes, estudiantes] = await Promise.allSettled([listarCohortes(), listarEstudiantes(LIMITE_MAXIMO_LISTADO, 0)]);
  return {
    laboratorios:
      cohortes.status === "fulfilled"
        ? cohortes.value
            .flatMap((c) => c.laboratorios)
            .map((lab) => ({ valor: String(lab.id), texto: `${lab.codigo} · ${lab.titulo}` }))
        : [],
    estudiantes:
      estudiantes.status === "fulfilled"
        ? estudiantes.value.items.map((e) => ({ valor: e.id, texto: nombreVisible(e.nombre, "Estudiante sin nombre") }))
        : null,
  };
}
