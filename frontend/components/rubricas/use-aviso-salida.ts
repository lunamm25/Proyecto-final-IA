"use client";

import { useEffect } from "react";

/** Pide confirmación al cerrar o recargar la pestaña si hay cambios sin guardar. */
export function useAvisoSalida(activo: boolean): void {
  useEffect(() => {
    if (!activo) return;
    function alSalir(evento: BeforeUnloadEvent) {
      evento.preventDefault();
    }
    window.addEventListener("beforeunload", alSalir);
    return () => window.removeEventListener("beforeunload", alSalir);
  }, [activo]);
}
