"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ErrorApi, mensajeDeError, obtenerYo } from "@/lib/api";
import { borrarSesionMock, leerSesionMock } from "@/lib/sesion-mock";
import { obtenerSupabaseNavegador } from "@/lib/supabase/cliente";
import type { Perfil } from "@/lib/tipos";

export type EstadoSesion = "cargando" | "anonimo" | "autenticado" | "error";

interface ValorSesion {
  estado: EstadoSesion;
  perfil: Perfil | null;
  error: string | null;
  recargar: () => Promise<void>;
  cerrarSesion: () => Promise<void>;
}

const ContextoSesion = createContext<ValorSesion | null>(null);

async function haySesionActiva(): Promise<boolean> {
  const supabase = obtenerSupabaseNavegador();
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    return data.session !== null;
  }
  return leerSesionMock() !== null;
}

export function ProveedorSesion({ children }: { children: React.ReactNode }) {
  const [estado, setEstado] = useState<EstadoSesion>("cargando");
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recargar = useCallback(async () => {
    try {
      if (!(await haySesionActiva())) {
        setPerfil(null);
        setError(null);
        setEstado("anonimo");
        return;
      }
      const datos = await obtenerYo();
      setPerfil(datos);
      setError(null);
      setEstado("autenticado");
    } catch (causa) {
      setPerfil(null);
      if (causa instanceof ErrorApi && causa.status === 401) {
        setError(null);
        setEstado("anonimo");
        return;
      }
      setError(mensajeDeError(causa));
      setEstado("error");
    }
  }, []);

  const cerrarSesion = useCallback(async () => {
    const supabase = obtenerSupabaseNavegador();
    if (supabase) await supabase.auth.signOut();
    borrarSesionMock();
    setPerfil(null);
    setError(null);
    setEstado("anonimo");
  }, []);

  useEffect(() => {
    let activo = true;
    const cargar = async () => {
      if (activo) await recargar();
    };
    void cargar();
    const supabase = obtenerSupabaseNavegador();
    const suscripcion = supabase?.auth.onAuthStateChange((evento) => {
      if (evento === "SIGNED_IN" || evento === "SIGNED_OUT" || evento === "USER_UPDATED") void cargar();
    });
    return () => {
      activo = false;
      suscripcion?.data.subscription.unsubscribe();
    };
  }, [recargar]);

  const valor = useMemo(
    () => ({ estado, perfil, error, recargar, cerrarSesion }),
    [estado, perfil, error, recargar, cerrarSesion],
  );

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>;
}

export function useSesion(): ValorSesion {
  const valor = useContext(ContextoSesion);
  if (!valor) throw new Error("useSesion debe usarse dentro de <ProveedorSesion>.");
  return valor;
}
