import type { Rol } from "@/lib/tipos";

interface ErrorAuth {
  message: string;
  code?: string;
}

/** Traduce los errores más comunes de Supabase Auth al español. */
export function traducirErrorAuth(error: ErrorAuth): string {
  const codigo = error.code ?? "";
  const mensaje = error.message.toLowerCase();
  if (codigo === "invalid_credentials" || mensaje.includes("invalid login credentials")) {
    return "Correo o contraseña incorrectos.";
  }
  if (codigo === "user_already_exists" || codigo === "email_exists" || mensaje.includes("already registered")) {
    return "Ya existe una cuenta con este correo. Inicia sesión.";
  }
  if (codigo === "weak_password" || mensaje.includes("password should be at least")) {
    return "La contraseña es muy corta o débil. Usa al menos 6 caracteres.";
  }
  if (codigo === "email_not_confirmed" || mensaje.includes("email not confirmed")) {
    return "Debes confirmar tu correo antes de iniciar sesión. Revisa tu bandeja de entrada.";
  }
  if (codigo === "over_request_rate_limit" || codigo === "over_email_send_rate_limit" || mensaje.includes("rate limit")) {
    return "Demasiados intentos. Espera unos minutos e inténtalo de nuevo.";
  }
  if (codigo === "validation_failed" || mensaje.includes("invalid format")) {
    return "El correo no tiene un formato válido.";
  }
  if (mensaje.includes("failed to fetch") || mensaje.includes("network")) {
    return "No se pudo conectar con el servicio de autenticación. Revisa tu conexión.";
  }
  return "No se pudo completar la operación. Intenta de nuevo.";
}

export const LONGITUD_MINIMA_CONTRASENA = 6;

export function validarEmail(email: string): string | null {
  if (email.trim() === "") return "Escribe tu correo.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return "El correo no tiene un formato válido.";
  return null;
}

export function validarContrasena(contrasena: string): string | null {
  if (contrasena === "") return "Escribe tu contraseña.";
  if (contrasena.length < LONGITUD_MINIMA_CONTRASENA) {
    return `La contraseña debe tener al menos ${LONGITUD_MINIMA_CONTRASENA} caracteres.`;
  }
  return null;
}

/** Ruta de inicio según el rol. */
export function rutaInicioPorRol(rol: Rol): string {
  return rol === "estudiante" ? "/portafolio" : "/docente";
}

/** Acepta solo rutas internas para evitar redirecciones abiertas. */
export function destinoSeguro(siguiente: string | null): string | null {
  if (!siguiente || !siguiente.startsWith("/") || siguiente.startsWith("//")) return null;
  return siguiente;
}
