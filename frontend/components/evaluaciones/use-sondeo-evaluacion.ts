"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorApi, mensajeDeError, obtenerEvaluacion } from "@/lib/api";
import type { Evaluacion, IdNumerico } from "@/lib/tipos";
import {
  INTERVALO_SONDEO_MS,
  MAX_FALLOS_SONDEO,
  estaProcesando,
} from "@/components/evaluaciones/estado-evaluacion";

export type EstadoSondeo =
  | { tipo: "cargando" }
  | { tipo: "error"; mensaje: string; status: number | null }
  | { tipo: "listo"; evaluacion: Evaluacion; fallos: number };

interface ResultadoSondeo {
  estado: EstadoSondeo;
  /** Vuelve a consultar desde cero (botón "Reintentar"). */
  reintentar: () => void;
  /** Reemplaza la evaluación mostrada por la que devolvió el backend tras una acción. */
  reemplazar: (evaluacion: Evaluacion) => void;
}

/** Errores que vale la pena reintentar durante el sondeo: sin conexión (0) o fallo del servidor (5xx). */
function esTransitorio(status: number | null): boolean {
  return status === 0 || (status !== null && status >= 500);
}

/**
 * Carga la evaluación y, mientras se esté procesando, la vuelve a consultar cada INTERVALO_SONDEO_MS.
 * Se detiene al llegar a un estado final, al desmontar o tras MAX_FALLOS_SONDEO fallos seguidos.
 */
export function useSondeoEvaluacion(id: IdNumerico): ResultadoSondeo {
  const [estado, setEstado] = useState<EstadoSondeo>({ tipo: "cargando" });
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let activo = true;
    let temporizador: ReturnType<typeof setTimeout> | undefined;
    let fallos = 0;
    let ultima: Evaluacion | null = null;

    const programar = () => {
      temporizador = setTimeout(() => void consultar(), INTERVALO_SONDEO_MS);
    };

    async function consultar(): Promise<void> {
      try {
        const evaluacion = await obtenerEvaluacion(id);
        if (!activo) return;
        fallos = 0;
        ultima = evaluacion;
        setEstado({ tipo: "listo", evaluacion, fallos });
        if (estaProcesando(evaluacion)) programar();
      } catch (causa) {
        if (!activo) return;
        fallos += 1;
        const status = causa instanceof ErrorApi ? causa.status : null;
        if (ultima && estaProcesando(ultima) && esTransitorio(status) && fallos < MAX_FALLOS_SONDEO) {
          setEstado({ tipo: "listo", evaluacion: ultima, fallos });
          programar();
          return;
        }
        setEstado({ tipo: "error", mensaje: mensajeDeError(causa), status });
      }
    }

    void consultar();
    return () => {
      activo = false;
      clearTimeout(temporizador);
    };
  }, [id, intento]);

  const reintentar = useCallback(() => {
    setEstado({ tipo: "cargando" });
    setIntento((valor) => valor + 1);
  }, []);

  const reemplazar = useCallback((evaluacion: Evaluacion) => {
    setEstado({ tipo: "listo", evaluacion, fallos: 0 });
  }, []);

  return { estado, reintentar, reemplazar };
}
