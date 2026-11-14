"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { listarCohortes, mensajeDeError, obtenerRubricaVigenteONula } from "@/lib/api";
import { idDesdeUrl, type Cohorte, type Evaluacion, type IdNumerico, type Laboratorio, type RubricaVersion } from "@/lib/tipos";

export interface Referencias {
  laboratorioId: IdNumerico | null;
  estudianteId: string | null;
}

/**
 * Laboratorio y estudiante de la evaluación: los del backend si algún día los envía; si no, los de la URL
 * (?lab=&est=) que pone la pantalla que enlazó. Si no hay ninguno, quedan en null y la vista lo explica.
 */
export function useReferenciasEvaluacion(evaluacion: Pick<Evaluacion, "laboratorio_id" | "estudiante_id">): Referencias {
  const parametros = useSearchParams();
  return {
    laboratorioId: evaluacion.laboratorio_id ?? idDesdeUrl(parametros.get("lab") ?? ""),
    estudianteId: evaluacion.estudiante_id ?? (parametros.get("est") || null),
  };
}

export interface ContextoEvaluacion {
  cargado: boolean;
  laboratorio: Laboratorio | null;
  /** Versión vigente de la rúbrica del laboratorio (el contrato no permite pedir una versión específica). */
  rubrica: RubricaVersion | null;
  errorRubrica: string | null;
}

interface Resultado extends Omit<ContextoEvaluacion, "cargado"> {
  clave: IdNumerico;
}

export function buscarLaboratorio(cohortes: Cohorte[], id: IdNumerico): Laboratorio | null {
  for (const cohorte of cohortes) {
    const laboratorio = cohorte.laboratorios.find((l) => l.id === id);
    if (laboratorio) return laboratorio;
  }
  return null;
}

async function cargarContexto(laboratorioId: IdNumerico): Promise<Resultado> {
  const [cohortes, rubrica] = await Promise.allSettled([
    listarCohortes(),
    obtenerRubricaVigenteONula(laboratorioId),
  ]);
  return {
    clave: laboratorioId,
    laboratorio: cohortes.status === "fulfilled" ? buscarLaboratorio(cohortes.value, laboratorioId) : null,
    rubrica: rubrica.status === "fulfilled" ? rubrica.value : null,
    errorRubrica: rubrica.status === "rejected" ? mensajeDeError(rubrica.reason) : null,
  };
}

/** Datos complementarios (título del laboratorio y rúbrica). Si fallan, la evaluación se muestra igual. */
export function useContextoEvaluacion(laboratorioId: IdNumerico | null): ContextoEvaluacion {
  const [resultado, setResultado] = useState<Resultado | null>(null);

  useEffect(() => {
    if (laboratorioId === null) return;
    let activo = true;
    void cargarContexto(laboratorioId).then((datos) => {
      if (activo) setResultado(datos);
    });
    return () => {
      activo = false;
    };
  }, [laboratorioId]);

  if (!resultado || resultado.clave !== laboratorioId) {
    return { cargado: false, laboratorio: null, rubrica: null, errorRubrica: null };
  }
  return {
    cargado: true,
    laboratorio: resultado.laboratorio,
    rubrica: resultado.rubrica,
    errorRubrica: resultado.errorRubrica,
  };
}
