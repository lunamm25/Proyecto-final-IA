// Validación en el cliente del formulario de laboratorio (RF-02 CA1). El backend hace la validación oficial.
import { idDesdeUrl, type Cohorte, type IdNumerico, type Laboratorio, type LaboratorioEntrada } from "@/lib/tipos";

export const MAX_CODIGO = 20;
export const MAX_TITULO = 150;

/** Valores del formulario como texto (el <select> de cohorte guarda el id como texto). */
export interface FormularioLaboratorio {
  cohorte_id: string;
  codigo: string;
  titulo: string;
  descripcion: string;
  objetivos: string;
}

export type CampoLaboratorio = keyof FormularioLaboratorio;

export type ErroresLaboratorio = Partial<Record<CampoLaboratorio, string>>;

export const LABORATORIO_VACIO: FormularioLaboratorio = {
  cohorte_id: "",
  codigo: "",
  titulo: "",
  descripcion: "",
  objetivos: "",
};

/** Formulario a partir de un laboratorio existente (descripción y objetivos pueden venir en null). */
export function formularioDesde(laboratorio: Laboratorio): FormularioLaboratorio {
  return {
    cohorte_id: String(laboratorio.cohorte_id),
    codigo: laboratorio.codigo,
    titulo: laboratorio.titulo,
    descripcion: laboratorio.descripcion ?? "",
    objetivos: laboratorio.objetivos ?? "",
  };
}

function codigoRepetido(datos: FormularioLaboratorio, cohortes: Cohorte[], idActual: IdNumerico | null): boolean {
  const cohorteId = idDesdeUrl(datos.cohorte_id);
  const cohorte = cohortes.find((c) => c.id === cohorteId);
  const codigo = datos.codigo.trim().toLowerCase();
  return Boolean(cohorte?.laboratorios.some((l) => l.id !== idActual && l.codigo.trim().toLowerCase() === codigo));
}

function errorCodigo(datos: FormularioLaboratorio, cohortes: Cohorte[], idActual: IdNumerico | null): string | undefined {
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
  datos: FormularioLaboratorio,
  cohortes: Cohorte[],
  idActual: IdNumerico | null,
): ErroresLaboratorio {
  const errores: ErroresLaboratorio = {};
  if (idDesdeUrl(datos.cohorte_id) === null) errores.cohorte_id = "Elige una cohorte.";
  const codigo = errorCodigo(datos, cohortes, idActual);
  if (codigo) errores.codigo = codigo;
  if (datos.titulo.trim() === "") errores.titulo = "El título es obligatorio.";
  else if (datos.titulo.trim().length > MAX_TITULO) errores.titulo = `Máximo ${MAX_TITULO} caracteres.`;
  if (datos.descripcion.trim() === "") errores.descripcion = "La descripción es obligatoria.";
  if (datos.objetivos.trim() === "") errores.objetivos = "Escribe al menos un objetivo.";
  return errores;
}

/** Convierte el formulario (ya validado) en el cuerpo de POST/PUT, con `cohorte_id` numérico. */
export function aEntradaLaboratorio(datos: FormularioLaboratorio): LaboratorioEntrada {
  return {
    cohorte_id: Number(datos.cohorte_id),
    codigo: datos.codigo.trim(),
    titulo: datos.titulo.trim(),
    descripcion: datos.descripcion.trim(),
    objetivos: datos.objetivos.trim(),
  };
}
