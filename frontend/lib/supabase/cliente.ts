import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { obtenerConfigSupabase } from "@/lib/supabase/config";

let cliente: SupabaseClient | null = null;

/** Cliente de Supabase para componentes de cliente. Devuelve null si Supabase no está configurado. */
export function obtenerSupabaseNavegador(): SupabaseClient | null {
  if (cliente) return cliente;
  const config = obtenerConfigSupabase();
  if (!config) return null;
  cliente = createBrowserClient(config.url, config.anonKey);
  return cliente;
}
