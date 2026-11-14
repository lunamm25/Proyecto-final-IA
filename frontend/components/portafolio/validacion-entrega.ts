// Validación en el cliente del formulario de entrega (RF-04 CA1 y §9). El backend vuelve a validar todo.

const MB = 1024 * 1024;

export const MAX_PDF_MB = 10;
export const MAX_ZIP_MB = 20;
export const MAX_IMAGENES = 5;
export const MAX_IMAGEN_MB = 5;

export const TIPOS_IMAGEN = ["image/png", "image/jpeg", "image/webp"];
export const EXTENSIONES_IMAGEN = [".png", ".jpg", ".jpeg", ".webp"];

/** https://github.com/usuario/repositorio (opcionalmente con .git o "/" final). */
export const PATRON_GITHUB = /^https:\/\/github\.com\/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\/[A-Za-z0-9._-]{1,100}?(?:\.git)?\/?$/;

export type ModoCodigo = "zip" | "github";

export type CampoEntrega = "pdf" | "zip" | "github_url" | "extras";

export type ErroresEntrega = Partial<Record<CampoEntrega, string>>;

export interface DatosFormulario {
  pdf: File | null;
  modoCodigo: ModoCodigo;
  zip: File | null;
  githubUrl: string;
  imagenes: File[];
}

function tieneExtension(archivo: File, extensiones: string[]): boolean {
  const nombre = archivo.name.toLowerCase();
  return extensiones.some((extension) => nombre.endsWith(extension));
}

export function formatearTamano(bytes: number): string {
  if (bytes < MB) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / MB).toFixed(1).replace(".", ",")} MB`;
}

export function validarPdf(archivo: File | null): string | undefined {
  if (!archivo) return "Adjunta el informe en PDF.";
  const tipoValido = archivo.type === "application/pdf" || archivo.type === "";
  if (!tipoValido || !tieneExtension(archivo, [".pdf"])) return "El informe debe ser un archivo PDF (.pdf).";
  if (archivo.size === 0) return "El PDF está vacío.";
  if (archivo.size > MAX_PDF_MB * MB) return `El PDF pesa ${formatearTamano(archivo.size)}; el máximo es ${MAX_PDF_MB} MB.`;
  return undefined;
}

export function validarZip(archivo: File | null): string | undefined {
  if (!archivo) return "Adjunta el código en un archivo ZIP.";
  if (!tieneExtension(archivo, [".zip"])) return "El código debe estar en un archivo .zip.";
  if (archivo.size === 0) return "El ZIP está vacío.";
  if (archivo.size > MAX_ZIP_MB * MB) return `El ZIP pesa ${formatearTamano(archivo.size)}; el máximo es ${MAX_ZIP_MB} MB.`;
  return undefined;
}

export function validarGithub(url: string): string | undefined {
  const limpia = url.trim();
  if (limpia === "") return "Escribe la URL del repositorio de GitHub.";
  if (!PATRON_GITHUB.test(limpia)) {
    return "La URL debe tener la forma https://github.com/usuario/repositorio (repositorio público).";
  }
  return undefined;
}

export function validarImagen(archivo: File): string | undefined {
  const tipoValido = TIPOS_IMAGEN.includes(archivo.type) && tieneExtension(archivo, EXTENSIONES_IMAGEN);
  if (!tipoValido) return `"${archivo.name}" no es una imagen PNG, JPG o WEBP.`;
  if (archivo.size > MAX_IMAGEN_MB * MB) {
    return `"${archivo.name}" pesa ${formatearTamano(archivo.size)}; el máximo por imagen es ${MAX_IMAGEN_MB} MB.`;
  }
  return undefined;
}

export function validarImagenes(imagenes: File[]): string | undefined {
  if (imagenes.length > MAX_IMAGENES) return `Puedes adjuntar como máximo ${MAX_IMAGENES} imágenes.`;
  for (const imagen of imagenes) {
    const error = validarImagen(imagen);
    if (error) return error;
  }
  return undefined;
}

/** Valida todo el formulario; devuelve solo los campos con error. */
export function validarFormulario(datos: DatosFormulario): ErroresEntrega {
  const errores: ErroresEntrega = {
    pdf: validarPdf(datos.pdf),
    zip: datos.modoCodigo === "zip" ? validarZip(datos.zip) : undefined,
    github_url: datos.modoCodigo === "github" ? validarGithub(datos.githubUrl) : undefined,
    extras: validarImagenes(datos.imagenes),
  };
  return Object.fromEntries(Object.entries(errores).filter(([, valor]) => valor !== undefined)) as ErroresEntrega;
}

/** Orden en que se enfoca el primer campo con error. */
export const ORDEN_CAMPOS: CampoEntrega[] = ["pdf", "zip", "github_url", "extras"];
