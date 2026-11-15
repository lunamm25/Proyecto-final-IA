// Sesión simulada solo para desarrollo: se usa cuando Supabase no está configurado
// y el modo mock está activo. No ofrece seguridad; la seguridad real la aplica el backend.

export const COOKIE_SESION_MOCK = "apa_sesion_mock";

/** La sesión simulada nunca se permite en producción (allí falta configuración y se muestra el error). */
export const SESION_SIMULADA_PERMITIDA = process.env.NODE_ENV !== "production";

export function leerSesionMock(): string | null {
  if (!SESION_SIMULADA_PERMITIDA || typeof document === "undefined") return null;
  const par = document.cookie.split("; ").find((valor) => valor.startsWith(`${COOKIE_SESION_MOCK}=`));
  if (!par) return null;
  return decodeURIComponent(par.slice(COOKIE_SESION_MOCK.length + 1)) || null;
}

export function guardarSesionMock(email: string): void {
  if (!SESION_SIMULADA_PERMITIDA) return;
  document.cookie = `${COOKIE_SESION_MOCK}=${encodeURIComponent(email)}; path=/; max-age=86400; samesite=lax`;
}

export function borrarSesionMock(): void {
  document.cookie = `${COOKIE_SESION_MOCK}=; path=/; max-age=0; samesite=lax`;
}
