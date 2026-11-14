"use client";

import { useEffect, useState } from "react";
import { listarUsuarios } from "@/lib/api";

/** Nombre del estudiante (GET /usuarios). Si no está disponible devuelve null; nunca se usa el correo. */
export function useNombreEstudiante(estudianteId: string): string | null {
  const [resultado, setResultado] = useState<{ id: string; nombre: string | null } | null>(null);

  useEffect(() => {
    let activo = true;
    listarUsuarios()
      .then((usuarios) => usuarios.find((u) => u.id === estudianteId)?.nombre ?? null)
      .catch(() => null)
      .then((nombre) => {
        if (activo) setResultado({ id: estudianteId, nombre });
      });
    return () => {
      activo = false;
    };
  }, [estudianteId]);

  return resultado?.id === estudianteId ? resultado.nombre : null;
}
