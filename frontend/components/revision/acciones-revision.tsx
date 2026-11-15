"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { estaProcesando, formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import { aprobarEvaluacion, mensajeDeError, pasarARevision, publicarEvaluacion } from "@/lib/api";
import type { Evaluacion, IdNumerico } from "@/lib/tipos";

type Accion = "revisar" | "aprobar" | "publicar";

const CONFIG_ACCION: Record<Accion, { boton: string; pregunta: string; ejecutar: (id: IdNumerico) => Promise<Evaluacion> }> = {
  revisar: {
    boton: "Iniciar revisión",
    pregunta: "¿Pasar esta evaluación a revisión? Podrás seguir ajustando niveles y textos, y después aprobarla.",
    ejecutar: pasarARevision,
  },
  aprobar: {
    boton: "Aprobar",
    pregunta: "¿Aprobar esta evaluación? Después ya no podrás ajustar los niveles.",
    ejecutar: aprobarEvaluacion,
  },
  publicar: {
    boton: "Publicar",
    pregunta: "¿Publicar esta evaluación? El estudiante podrá ver la nota y la retroalimentación.",
    ejecutar: publicarEvaluacion,
  },
};

/**
 * Acción disponible según el estado (RF-07 CA3), igual que el backend:
 * borrador → revisar → en_revision → aprobar → aprobada → publicar → publicada.
 */
function accionDisponible(evaluacion: Evaluacion): Accion | null {
  if (estaProcesando(evaluacion)) return null;
  if (evaluacion.estado === "borrador") return "revisar";
  if (evaluacion.estado === "en_revision") return "aprobar";
  if (evaluacion.estado === "aprobada") return "publicar";
  return null;
}

function TextoSinAccion({ evaluacion }: { evaluacion: Evaluacion }) {
  if (evaluacion.estado === "publicada") {
    const fecha = evaluacion.publicada_en ? ` el ${formatearFechaHora(evaluacion.publicada_en)}` : "";
    return <p className="text-sm text-emerald-800">Publicada{fecha}. El estudiante ya puede verla.</p>;
  }
  if (evaluacion.estado === "error") {
    return <p className="text-sm text-destructive">La evaluación terminó con error: no se puede aprobar ni publicar.</p>;
  }
  return <p className="text-sm text-muted-foreground">Espera a que termine el procesamiento.</p>;
}

interface ConfirmacionProps {
  accion: Accion;
  enviando: boolean;
  alConfirmar: () => void;
  alCancelar: () => void;
}

function Confirmacion({ accion, enviando, alConfirmar, alCancelar }: ConfirmacionProps) {
  const refConfirmar = useRef<HTMLButtonElement>(null);
  useEffect(() => refConfirmar.current?.focus(), []);
  return (
    <div role="alertdialog" aria-labelledby="pregunta-accion" className="rounded-lg border border-amber-300 bg-amber-50 p-3">
      <p id="pregunta-accion" className="text-sm text-amber-900">{CONFIG_ACCION[accion].pregunta}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button ref={refConfirmar} onClick={alConfirmar} disabled={enviando} aria-busy={enviando}>
          {enviando && <Loader2 className="animate-spin" aria-hidden="true" />}
          Sí, {CONFIG_ACCION[accion].boton.toLowerCase()}
        </Button>
        <Button variant="outline" onClick={alCancelar} disabled={enviando}>Cancelar</Button>
      </div>
    </div>
  );
}

/** Botones Aprobar / Publicar con confirmación previa. Muestra el detalle del backend si falla (p. ej. 409). */
export function AccionesRevision({ evaluacion, alCambiar }: { evaluacion: Evaluacion; alCambiar: (e: Evaluacion) => void }) {
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const accion = accionDisponible(evaluacion);

  if (!accion) return <TextoSinAccion evaluacion={evaluacion} />;

  async function confirmar(actual: Accion) {
    setEnviando(true);
    setError(null);
    try {
      const nueva = await CONFIG_ACCION[actual].ejecutar(evaluacion.id);
      setConfirmando(false);
      alCambiar(nueva);
    } catch (causa) {
      setError(mensajeDeError(causa));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-2">
      {confirmando ? (
        <Confirmacion
          accion={accion}
          enviando={enviando}
          alConfirmar={() => void confirmar(accion)}
          alCancelar={() => setConfirmando(false)}
        />
      ) : (
        <Button onClick={() => setConfirmando(true)}>{CONFIG_ACCION[accion].boton}</Button>
      )}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
