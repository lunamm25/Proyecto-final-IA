import type { ConfigIA, ConfigIAEntrada, ProveedorIA } from "@/lib/tipos";

/** RNF-02: temperatura ≤ 0,2 para que las evaluaciones sean reproducibles. */
export const TEMPERATURA_MINIMA = 0;
export const TEMPERATURA_MAXIMA = 0.2;
/** Solo para las flechas del campo; se acepta cualquier valor entre el mínimo y el máximo. */
export const PASO_TEMPERATURA = 0.01;
export const MAX_MODELO = 100;

export interface OpcionProveedor {
  valor: ProveedorIA;
  etiqueta: string;
  descripcion: string;
}

export const OPCIONES_PROVEEDOR: OpcionProveedor[] = [
  { valor: "gemini", etiqueta: "Gemini", descripcion: "Modelos Flash de Google; leen PDF e imágenes." },
  {
    valor: "openai_compatible",
    etiqueta: "OpenAI-compatible (Ollama, Groq, OpenRouter)",
    descripcion: "Cualquier servidor con API compatible con OpenAI, incluido un modelo local con Ollama.",
  },
];

export const TEXTO_PROVEEDOR: Record<ProveedorIA, string> = {
  gemini: "Gemini",
  openai_compatible: "OpenAI-compatible",
};

/** Solo sugerencias para el <datalist>: se puede escribir cualquier otro modelo. */
export const SUGERENCIAS_MODELO: Record<ProveedorIA, string[]> = {
  gemini: ["gemini-3.5-flash-lite"],
  openai_compatible: ["llama3.1", "llama3.1:8b", "qwen2.5", "mistral", "llama-3.1-8b-instant"],
};

export interface FormularioConfig {
  proveedor: ProveedorIA;
  modelo: string;
  /** Texto del campo numérico; se convierte a número al enviar. */
  temperatura: string;
}

export type ErroresConfig = Partial<Record<"modelo" | "temperatura", string>>;

/** Copia solo los campos del contrato: si el backend enviara otros (p. ej. URL o clave), se descartan. */
export function limpiarConfig(config: ConfigIA): ConfigIA {
  return {
    proveedor: config.proveedor,
    modelo: config.modelo,
    temperatura: config.temperatura,
    actualizado_por: config.actualizado_por,
    actualizado_en: config.actualizado_en,
  };
}

export function aFormulario(config: ConfigIA): FormularioConfig {
  return { proveedor: config.proveedor, modelo: config.modelo, temperatura: String(config.temperatura) };
}

/** Cuerpo del PUT: solo proveedor, modelo y temperatura. */
export function aEntrada(formulario: FormularioConfig): ConfigIAEntrada {
  return {
    proveedor: formulario.proveedor,
    modelo: formulario.modelo.trim(),
    temperatura: Number(formulario.temperatura),
  };
}

function errorModelo(modelo: string): string | undefined {
  if (modelo.trim() === "") return "Escribe el nombre del modelo.";
  if (modelo.trim().length > MAX_MODELO) return `El nombre del modelo no puede superar ${MAX_MODELO} caracteres.`;
  return undefined;
}

function errorTemperatura(texto: string): string | undefined {
  if (texto.trim() === "") return "Escribe la temperatura.";
  const valor = Number(texto);
  if (!Number.isFinite(valor)) return "La temperatura debe ser un número.";
  if (valor < TEMPERATURA_MINIMA || valor > TEMPERATURA_MAXIMA) {
    return "La temperatura debe estar entre 0 y 0,2 para que las evaluaciones sean reproducibles.";
  }
  return undefined;
}

export function validarConfig(formulario: FormularioConfig): ErroresConfig {
  const errores: ErroresConfig = {};
  const modelo = errorModelo(formulario.modelo);
  const temperatura = errorTemperatura(formulario.temperatura);
  if (modelo) errores.modelo = modelo;
  if (temperatura) errores.temperatura = temperatura;
  return errores;
}

export function hayCambios(formulario: FormularioConfig, guardada: ConfigIA): boolean {
  return (
    formulario.proveedor !== guardada.proveedor ||
    formulario.modelo.trim() !== guardada.modelo ||
    Number(formulario.temperatura) !== guardada.temperatura
  );
}

export function formatearTemperatura(valor: number): string {
  return valor.toLocaleString("es-CO", { maximumFractionDigits: 2 });
}
