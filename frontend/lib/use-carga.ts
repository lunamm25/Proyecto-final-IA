"use client";

import { useCallback, useEffect, useState } from "react";
import { mensajeDeError } from "@/lib/api";

export type EstadoCarga<T> =
  | { tipo: "cargando" }
  | { tipo: "error"; mensaje: string }
  | { tipo: "listo"; datos: T };

interface ResultadoCarga<T> {
  estado: EstadoCarga<T>;
  /** Vuelve a cargar mostrando el estado de carga (p. ej. botón "Reintentar"). */
  recargar: () => void;
  /** Vuelve a cargar sin ocultar los datos actuales (p. ej. tras una acción). */
  refrescar: () => void;
}

/** Ejecuta `cargar` al montar y cada vez que se pide recargar; `cargar` debe ser estable (useCallback). */
export function useCarga<T>(cargar: () => Promise<T>): ResultadoCarga<T> {
  const [estado, setEstado] = useState<EstadoCarga<T>>({ tipo: "cargando" });
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let activo = true;
    cargar()
      .then((datos) => {
        if (activo) setEstado({ tipo: "listo", datos });
      })
      .catch((causa: unknown) => {
        if (activo) setEstado({ tipo: "error", mensaje: mensajeDeError(causa) });
      });
    return () => {
      activo = false;
    };
  }, [cargar, intento]);

  const refrescar = useCallback(() => setIntento((valor) => valor + 1), []);

  const recargar = useCallback(() => {
    setEstado({ tipo: "cargando" });
    refrescar();
  }, [refrescar]);

  return { estado, recargar, refrescar };
}
