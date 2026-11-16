"use client";

import { useEffect, useState } from "react";
import { listarUsuarios } from "@/lib/api";

/**
 * Nombre del estudiante (GET /usuarios, que en el backend es solo para admin). Si no se puede consultar, devuelve
 * null y la vista muestra un texto genérico; nunca se usa el correo.
 */
export function useNombreEstudiante(estudianteId: string | null): string | null {
  const [resultado, setResultado] = useState<{ id: string; nombre: string | null } | null>(null);

  useEffect(() => {
    if (!estudianteId) return;
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

  return estudianteId && resultado?.id === estudianteId ? resultado.nombre : null;
}
