// Validación en el cliente del formulario de laboratorio (RF-02 CA1). El backend hace la validación oficial.
import type { Cohorte, LaboratorioEntrada } from "@/lib/tipos";

export const MAX_CODIGO = 20;
export const MAX_TITULO = 150;

export type CampoLaboratorio = keyof LaboratorioEntrada;

export type ErroresLaboratorio = Partial<Record<CampoLaboratorio, string>>;

export const LABORATORIO_VACIO: LaboratorioEntrada = {
  cohorte_id: "",
  codigo: "",
  titulo: "",
  descripcion: "",
  objetivos: "",
};

function codigoRepetido(datos: LaboratorioEntrada, cohortes: Cohorte[], idActual: string | null): boolean {
  const cohorte = cohortes.find((c) => c.id === datos.cohorte_id);
  const codigo = datos.codigo.trim().toLowerCase();
  return Boolean(cohorte?.laboratorios.some((l) => l.id !== idActual && l.codigo.trim().toLowerCase() === codigo));
}

function errorCodigo(datos: LaboratorioEntrada, cohortes: Cohorte[], idActual: string | null): string | undefined {
  const codigo = datos.codigo.trim();
  if (codigo === "") return "El código es obligatorio.";
  if (codigo.length > MAX_CODIGO) return `El código no puede tener más de ${MAX_CODIGO} caracteres.`;
  if (datos.cohorte_id !== "" && codigoRepetido(datos, cohortes, idActual)) {
    return "Ya existe un laboratorio con este código en la cohorte elegida.";
  }
  return undefined;
}

/** Devuelve un mensaje por cada campo con error (objeto vacío = formulario válido). */
export function validarLaboratorio(
  datos: LaboratorioEntrada,
  cohortes: Cohorte[],
  idActual: string | null,
): ErroresLaboratorio {
  const errores: ErroresLaboratorio = {};
  if (datos.cohorte_id === "") errores.cohorte_id = "Elige una cohorte.";
  const codigo = errorCodigo(datos, cohortes, idActual);
  if (codigo) errores.codigo = codigo;
  if (datos.titulo.trim() === "") errores.titulo = "El título es obligatorio.";
  else if (datos.titulo.trim().length > MAX_TITULO) errores.titulo = `Máximo ${MAX_TITULO} caracteres.`;
  if (datos.descripcion.trim() === "") errores.descripcion = "La descripción es obligatoria.";
  if (datos.objetivos.trim() === "") errores.objetivos = "Escribe al menos un objetivo.";
  return errores;
}

/** Quita espacios sobrantes antes de enviar al backend. */
export function limpiarLaboratorio(datos: LaboratorioEntrada): LaboratorioEntrada {
  return {
    cohorte_id: datos.cohorte_id,
    codigo: datos.codigo.trim(),
    titulo: datos.titulo.trim(),
    descripcion: datos.descripcion.trim(),
    objetivos: datos.objetivos.trim(),
  };
}
