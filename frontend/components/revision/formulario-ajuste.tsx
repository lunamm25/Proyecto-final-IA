"use client";

import { useId, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatearNota } from "@/components/portafolio/estado-entrega";
import { ajustarCriterio, mensajeDeError } from "@/lib/api";
import type { EvaluacionCriterio, Evaluacion, NivelDesempeno } from "@/lib/tipos";

/** Longitud mínima del motivo de un ajuste (RF-07 CA2: la justificación es obligatoria). */
export const MIN_CARACTERES_MOTIVO = 10;

interface FormularioAjusteProps {
  evaluacionId: string;
  criterio: EvaluacionCriterio;
  /** Niveles del criterio según la rúbrica; null si no se pudieron cargar. */
  niveles: NivelDesempeno[] | null;
  /** Motivo por el que no se permite ajustar (estado aprobada/publicada, etc.); null si se permite. */
  bloqueo: string | null;
  alAjustar: (evaluacion: Evaluacion) => void;
}

interface Errores {
  nivel?: string;
  motivo?: string;
}

function validar(nivel: string, motivo: string, nivelActual: string): Errores {
  const errores: Errores = {};
  if (nivel === "") errores.nivel = "Elige un nivel.";
  else if (nivel === nivelActual) errores.nivel = "Elige un nivel distinto al nivel final actual.";
  const largo = motivo.trim().length;
  if (largo === 0) errores.motivo = "El motivo del ajuste es obligatorio.";
  else if (largo < MIN_CARACTERES_MOTIVO) {
    errores.motivo = `Explica el motivo con al menos ${MIN_CARACTERES_MOTIVO} caracteres (llevas ${largo}).`;
  }
  return errores;
}

type Envio = { tipo: "inactivo" } | { tipo: "enviando" } | { tipo: "error"; mensaje: string } | { tipo: "exito"; mensaje: string };

function mensajeExito(evaluacion: Evaluacion): string {
  const nota = evaluacion.nota === null ? "sin nota" : `${formatearNota(evaluacion.nota)} / 5,0`;
  return `Ajuste guardado. Nota recalculada por el sistema: ${nota}.`;
}

/** Cambia el nivel de un criterio con motivo obligatorio. La nota la recalcula el backend. */
export function FormularioAjuste({ evaluacionId, criterio, niveles, bloqueo, alAjustar }: FormularioAjusteProps) {
  const base = useId();
  const [nivel, setNivel] = useState(criterio.nivel_final);
  const [motivo, setMotivo] = useState("");
  const [errores, setErrores] = useState<Errores>({});
  const [envio, setEnvio] = useState<Envio>({ tipo: "inactivo" });

  if (bloqueo) return <p className="text-sm text-muted-foreground">{bloqueo}</p>;
  if (!niveles || niveles.length === 0) {
    return (
      <p role="alert" className="text-sm text-destructive">
        No se pudieron cargar los niveles de este criterio desde la rúbrica; no es posible ajustarlo ahora.
      </p>
    );
  }

  async function enviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const nuevos = validar(nivel, motivo, criterio.nivel_final);
    setErrores(nuevos);
    if (nuevos.nivel || nuevos.motivo) return;
    setEnvio({ tipo: "enviando" });
    try {
      const evaluacion = await ajustarCriterio(evaluacionId, criterio.criterio_id, { nivel_final: nivel, motivo: motivo.trim() });
      setMotivo("");
      setEnvio({ tipo: "exito", mensaje: mensajeExito(evaluacion) });
      alAjustar(evaluacion);
    } catch (causa) {
      setEnvio({ tipo: "error", mensaje: mensajeDeError(causa) });
    }
  }

  const enviando = envio.tipo === "enviando";
  const idNivel = `${base}-nivel`;
  const idMotivo = `${base}-motivo`;

  return (
    <form noValidate onSubmit={(e) => void enviar(e)} className="space-y-3 rounded-lg border border-dashed p-3">
      <h4 className="text-sm font-semibold">Ajustar nivel</h4>
      <div className="flex flex-col gap-1">
        <label htmlFor={idNivel} className="text-sm font-medium">Nuevo nivel</label>
        <select
          id={idNivel}
          value={nivel}
          onChange={(e) => setNivel(e.target.value)}
          aria-invalid={errores.nivel ? true : undefined}
          aria-describedby={errores.nivel ? `${idNivel}-error` : undefined}
          className="h-9 rounded-lg border bg-background px-3 text-sm aria-invalid:border-destructive sm:max-w-xs"
        >
          {niveles.map((n) => (
            <option key={n.nombre} value={n.nombre}>
              {n.nombre} ({n.puntaje} pts){n.nombre === criterio.nivel_final ? " — actual" : ""}
            </option>
          ))}
        </select>
        {errores.nivel && <p id={`${idNivel}-error`} className="text-xs text-destructive">{errores.nivel}</p>}
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor={idMotivo} className="text-sm font-medium">Motivo del ajuste (obligatorio)</label>
        <textarea
          id={idMotivo}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          rows={3}
          required
          aria-invalid={errores.motivo ? true : undefined}
          aria-describedby={`${idMotivo}-ayuda${errores.motivo ? ` ${idMotivo}-error` : ""}`}
          className="rounded-lg border bg-background p-2 text-sm aria-invalid:border-destructive"
        />
        <p id={`${idMotivo}-ayuda`} className="text-xs text-muted-foreground">
          Queda registrado en la auditoría. Mínimo {MIN_CARACTERES_MOTIVO} caracteres.
        </p>
        {errores.motivo && <p id={`${idMotivo}-error`} className="text-xs text-destructive">{errores.motivo}</p>}
      </div>
      <Button type="submit" disabled={enviando} aria-busy={enviando}>
        {enviando && <Loader2 className="animate-spin" aria-hidden="true" />}
        Guardar ajuste
      </Button>
      <div aria-live="polite">
        {envio.tipo === "exito" && <p className="text-sm text-emerald-800">{envio.mensaje}</p>}
        {envio.tipo === "error" && <p role="alert" className="text-sm text-destructive">{envio.mensaje}</p>}
      </div>
    </form>
  );
}
