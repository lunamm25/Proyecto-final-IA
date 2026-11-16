// Rutas a una evaluación. EvaluacionRespuesta del backend no trae el laboratorio ni el estudiante (pedido a Rol 2),
// así que quien enlaza y sí los conoce (portafolio, bandeja, informe) los pasa en la URL como ?lab=&est=.
import type { IdNumerico } from "@/lib/tipos";

export interface ReferenciasEvaluacion {
  laboratorioId?: IdNumerico | null;
  /** UUID del estudiante. */
  estudianteId?: string | null;
}

function consulta({ laboratorioId, estudianteId }: ReferenciasEvaluacion = {}): string {
  const parametros = new URLSearchParams();
  if (laboratorioId !== undefined && laboratorioId !== null) parametros.set("lab", String(laboratorioId));
  if (estudianteId) parametros.set("est", estudianteId);
  const texto = parametros.toString();
  return texto ? `?${texto}` : "";
}

export function rutaEvaluacion(id: IdNumerico, referencias?: ReferenciasEvaluacion): string {
  return `/evaluaciones/${id}${consulta(referencias)}`;
}

export function rutaRevision(id: IdNumerico, referencias?: ReferenciasEvaluacion): string {
  return `/docente/revision/${id}${consulta(referencias)}`;
}
