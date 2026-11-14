import { NextResponse, type NextRequest } from "next/server";
import { COOKIE_SESION_MOCK, SESION_SIMULADA_PERMITIDA } from "@/lib/sesion-mock";
import { supabaseConfigurado } from "@/lib/supabase/config";
import { actualizarSesion } from "@/lib/supabase/proxy";

// Verificación optimista (UX): la seguridad real la aplica el backend con el JWT.
const RUTAS_PRIVADAS = ["/portafolio", "/informe", "/mapa", "/evaluaciones", "/docente", "/admin"];

function esPrivada(ruta: string): boolean {
  return RUTAS_PRIVADAS.some((prefijo) => ruta === prefijo || ruta.startsWith(`${prefijo}/`));
}

export async function proxy(request: NextRequest) {
  const { respuesta, haySesion: sesionSupabase } = await actualizarSesion(request);
  const haySesion = supabaseConfigurado()
    ? sesionSupabase
    : SESION_SIMULADA_PERMITIDA && request.cookies.has(COOKIE_SESION_MOCK);

  const { pathname, search } = request.nextUrl;
  if (!esPrivada(pathname) || haySesion) return respuesta;

  const destino = request.nextUrl.clone();
  destino.pathname = "/login";
  destino.search = `?siguiente=${encodeURIComponent(`${pathname}${search}`)}`;
  const redireccion = NextResponse.redirect(destino);
  respuesta.cookies.getAll().forEach((cookie) => redireccion.cookies.set(cookie));
  return redireccion;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
