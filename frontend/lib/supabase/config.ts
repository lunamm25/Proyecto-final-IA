export const MENSAJE_SUPABASE_NO_CONFIGURADO =
  "Supabase no está configurado: faltan NEXT_PUBLIC_SUPABASE_URL o NEXT_PUBLIC_SUPABASE_ANON_KEY en frontend/.env.local (ver .env.example).";

export interface ConfigSupabase {
  url: string;
  anonKey: string;
}

export function obtenerConfigSupabase(): ConfigSupabase | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return null;
  return { url, anonKey };
}

export function supabaseConfigurado(): boolean {
  return obtenerConfigSupabase() !== null;
}
