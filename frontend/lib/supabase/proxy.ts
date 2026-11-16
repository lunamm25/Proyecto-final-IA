import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { obtenerConfigSupabase } from "@/lib/supabase/config";

export interface ResultadoSesion {
  respuesta: NextResponse;
  haySesion: boolean;
}

/** Refresca la sesión de Supabase en cada petición (patrón oficial de @supabase/ssr). */
export async function actualizarSesion(request: NextRequest): Promise<ResultadoSesion> {
  let respuesta = NextResponse.next({ request });
  const config = obtenerConfigSupabase();
  if (!config) return { respuesta, haySesion: false };

  const supabase = createServerClient(config.url, config.anonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesPorGuardar, cabeceras) {
        cookiesPorGuardar.forEach(({ name, value }) => request.cookies.set(name, value));
        respuesta = NextResponse.next({ request });
        cookiesPorGuardar.forEach(({ name, value, options }) => respuesta.cookies.set(name, value, options));
        Object.entries(cabeceras).forEach(([clave, valor]) => respuesta.headers.set(clave, valor));
      },
    },
  });

  try {
    const { data } = await supabase.auth.getClaims();
    return { respuesta, haySesion: Boolean(data?.claims?.sub) };
  } catch {
    return { respuesta, haySesion: false };
  }
}
