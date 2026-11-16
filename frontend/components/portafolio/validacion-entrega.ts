// Validación en el cliente del formulario de entrega (RF-04 CA1 y §9), con las reglas de services/entregas.py.
// PDF obligatorio; ZIP y URL de GitHub opcionales. El backend vuelve a validar todo (PDF con texto, ZIP
// descomprimido, etc.) y responde 413/422/503 con `detail`.

const MB = 1024 * 1024;

/** Tamaño máximo del PDF y del ZIP (el backend responde 413 si se supera). */
export const MAX_PDF_MB = 20;
export const MAX_ZIP_MB = 20;
export const MAX_URL_GITHUB = 300;

/** Mismo patrón que PATRON_GITHUB del backend: https://github.com/<usuario>/<repositorio>[/ruta]. */
export const PATRON_GITHUB = /^https:\/\/github\.com\/[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100}(?:\/[A-Za-z0-9._-]+)*\/?$/;

/** Mismo texto que MSG_PDF_OBLIGATORIO del backend. */
export const MENSAJE_PDF_OBLIGATORIO = "El informe en PDF es obligatorio.";

export type CampoEntrega = "pdf" | "zip" | "github_url";

export type ErroresEntrega = Partial<Record<CampoEntrega, string>>;

export interface DatosFormulario {
  pdf: File | null;
  zip: File | null;
  githubUrl: string;
}

function tieneExtension(archivo: File, extensiones: string[]): boolean {
  const nombre = archivo.name.toLowerCase();
  return extensiones.some((extension) => nombre.endsWith(extension));
}

export function formatearTamano(bytes: number): string {
  if (bytes < MB) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / MB).toFixed(1).replace(".", ",")} MB`;
}

/** Revisa el PDF elegido: .pdf, no vacío y como máximo 20 MB. Que falte se revisa en validarFormulario. */
export function validarPdf(archivo: File | null): string | undefined {
  if (!archivo) return undefined;
  const tipoValido = archivo.type === "application/pdf" || archivo.type === "";
  if (!tipoValido || !tieneExtension(archivo, [".pdf"])) return "El informe debe ser un archivo PDF (.pdf).";
  if (archivo.size === 0) return "El PDF está vacío.";
  if (archivo.size > MAX_PDF_MB * MB) return `El PDF pesa ${formatearTamano(archivo.size)}; el máximo es ${MAX_PDF_MB} MB.`;
  return undefined;
}

/** ZIP opcional: si se adjunta, debe ser .zip y pesar como máximo 20 MB. */
export function validarZip(archivo: File | null): string | undefined {
  if (!archivo) return undefined;
  if (!tieneExtension(archivo, [".zip"])) return "El código debe estar en un archivo .zip.";
  if (archivo.size === 0) return "El ZIP está vacío.";
  if (archivo.size > MAX_ZIP_MB * MB) return `El ZIP pesa ${formatearTamano(archivo.size)}; el máximo es ${MAX_ZIP_MB} MB.`;
  return undefined;
}

/** URL opcional: si se escribe, debe ser un repositorio público de GitHub. */
export function validarGithub(url: string): string | undefined {
  const limpia = url.trim();
  if (limpia === "") return undefined;
  if (limpia.length > MAX_URL_GITHUB || !PATRON_GITHUB.test(limpia)) {
    return "La URL debe tener la forma https://github.com/usuario/repositorio, sin credenciales, parámetros ni espacios.";
  }
  return undefined;
}

/** Valida todo el formulario; devuelve solo los campos con error. */
export function validarFormulario(datos: DatosFormulario): ErroresEntrega {
  const errores: ErroresEntrega = {
    pdf: datos.pdf ? validarPdf(datos.pdf) : MENSAJE_PDF_OBLIGATORIO,
    zip: validarZip(datos.zip),
    github_url: validarGithub(datos.githubUrl),
  };
  return Object.fromEntries(Object.entries(errores).filter(([, valor]) => valor !== undefined)) as ErroresEntrega;
}

/** Orden en que se enfoca el primer campo con error. */
export const ORDEN_CAMPOS: CampoEntrega[] = ["pdf", "zip", "github_url"];
