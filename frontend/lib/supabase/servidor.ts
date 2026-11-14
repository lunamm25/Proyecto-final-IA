import { createServerClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { obtenerConfigSupabase } from "@/lib/supabase/config";

/** Cliente de Supabase para Server Components, Server Actions y Route Handlers. Devuelve null si no está configurado. */
export async function crearSupabaseServidor(): Promise<SupabaseClient | null> {
  const config = obtenerConfigSupabase();
  if (!config) return null;
  const almacen = await cookies();
  return createServerClient(config.url, config.anonKey, {
    cookies: {
      getAll() {
        return almacen.getAll();
      },
      setAll(cookiesPorGuardar) {
        try {
          cookiesPorGuardar.forEach(({ name, value, options }) => almacen.set(name, value, options));
        } catch {
          // En un Server Component no se pueden escribir cookies; el proxy ya refresca la sesión.
        }
      },
    },
  });
}
