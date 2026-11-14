import type { ConfigIA, ConfigIAEntrada, ProveedorIA, ProveedorPermitido } from "@/lib/tipos";

/** RNF-02: temperatura ≤ 0,2 para que las evaluaciones sean reproducibles (el backend envía el máximo vigente). */
export const TEMPERATURA_MINIMA = 0;
export const TEMPERATURA_MAXIMA = 0.2;
/** Solo para las flechas del campo; se acepta cualquier valor entre el mínimo y el máximo. */
export const PASO_TEMPERATURA = 0.01;

export interface FormularioConfig {
  proveedor: ProveedorIA;
  modelo: string;
  /** Texto del campo numérico; se convierte a número al enviar. */
  temperatura: string;
}

export type ErroresConfig = Partial<Record<"proveedor" | "modelo" | "temperatura", string>>;

/**
 * Copia solo los campos del contrato (ConfigIARespuesta): si el backend enviara algo más (p. ej. una URL o una clave),
 * se descarta y nunca se pinta. De las claves solo se guardan booleanos.
 */
export function limpiarConfig(config: ConfigIA): ConfigIA {
  return {
    proveedor: config.proveedor,
    modelo: config.modelo,
    temperatura: config.temperatura,
    origen: config.origen,
    modelo_permitido: config.modelo_permitido,
    actualizado_por: config.actualizado_por ? { id: config.actualizado_por.id, nombre: config.actualizado_por.nombre } : null,
    actualizado_en: config.actualizado_en,
    temperatura_maxima: config.temperatura_maxima,
    claves: {
      gemini_api_key_configurada: config.claves.gemini_api_key_configurada === true,
      openai_compat_api_key_configurada: config.claves.openai_compat_api_key_configurada === true,
      openai_compat_base_url_configurada: config.claves.openai_compat_base_url_configurada === true,
    },
    proveedores_permitidos: config.proveedores_permitidos.map((p) => ({
      proveedor: p.proveedor,
      etiqueta: p.etiqueta,
      modelos: [...p.modelos],
      modelos_probados: [...p.modelos_probados],
    })),
    versiones_prompt: { ...config.versiones_prompt },
  };
}

export function proveedorPermitido(config: ConfigIA, proveedor: ProveedorIA): ProveedorPermitido | undefined {
  return config.proveedores_permitidos.find((p) => p.proveedor === proveedor);
}

/** Etiqueta del proveedor según el backend (o su nombre si no está en la lista). */
export function etiquetaProveedor(config: ConfigIA, proveedor: ProveedorIA): string {
  return proveedorPermitido(config, proveedor)?.etiqueta ?? proveedor;
}

/** Un modelo está "sin probar" si no aparece en `modelos_probados` de su proveedor. */
export function estaProbado(permitido: ProveedorPermitido | undefined, modelo: string): boolean {
  return permitido?.modelos_probados.includes(modelo) ?? false;
}

/** Al cambiar de proveedor se propone el primer modelo probado (o el primero de la lista). */
export function modeloSugerido(permitido: ProveedorPermitido | undefined): string {
  if (!permitido) return "";
  return permitido.modelos.find((m) => permitido.modelos_probados.includes(m)) ?? permitido.modelos[0] ?? "";
}

/** Temperatura máxima: la del backend, nunca por encima de 0,2 (RNF-02). */
export function temperaturaMaxima(config: ConfigIA): number {
  return Math.min(config.temperatura_maxima, TEMPERATURA_MAXIMA);
}

export function aFormulario(config: ConfigIA): FormularioConfig {
  return { proveedor: config.proveedor, modelo: config.modelo, temperatura: String(config.temperatura) };
}

/** Cuerpo del PUT: siempre los tres campos juntos. */
export function aEntrada(formulario: FormularioConfig): ConfigIAEntrada {
  return { proveedor: formulario.proveedor, modelo: formulario.modelo, temperatura: Number(formulario.temperatura) };
}

function errorTemperatura(texto: string, maxima: number): string | undefined {
  if (texto.trim() === "") return "Escribe la temperatura.";
  const valor = Number(texto);
  if (!Number.isFinite(valor)) return "La temperatura debe ser un número.";
  if (valor < TEMPERATURA_MINIMA || valor > maxima) {
    return `La temperatura debe estar entre 0 y ${formatearTemperatura(maxima)} para que las evaluaciones sean reproducibles.`;
  }
  return undefined;
}

/** Validación en el cliente (la oficial es la del backend, que responde 422 con el motivo). */
export function validarConfig(formulario: FormularioConfig, config: ConfigIA): ErroresConfig {
  const errores: ErroresConfig = {};
  const permitido = proveedorPermitido(config, formulario.proveedor);
  if (!permitido) errores.proveedor = "Elige un proveedor de la lista.";
  else if (!permitido.modelos.includes(formulario.modelo)) errores.modelo = "Elige un modelo de la lista.";
  const temperatura = errorTemperatura(formulario.temperatura, temperaturaMaxima(config));
  if (temperatura) errores.temperatura = temperatura;
  return errores;
}

export function hayCambios(formulario: FormularioConfig, guardada: ConfigIA): boolean {
  return (
    formulario.proveedor !== guardada.proveedor ||
    formulario.modelo !== guardada.modelo ||
    Number(formulario.temperatura) !== guardada.temperatura
  );
}

export function formatearTemperatura(valor: number): string {
  return valor.toLocaleString("es-CO", { maximumFractionDigits: 2 });
}
