"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Aviso } from "@/components/docente/aviso";
import { CampoArchivo } from "@/components/portafolio/campo-archivo";
import { extraerRubrica, mensajeDeError } from "@/lib/api";
import type { ResultadoExtraccion } from "@/lib/tipos";

/** El backend solo acepta el enunciado en PDF con texto, de hasta 20 MB. */
export const MAX_RUBRICA_MB = 20;

/** Valida tipo y tamaño en el cliente; el backend vuelve a validar (413/422 con su mensaje). */
export function validarArchivoRubrica(archivo: File): string | undefined {
  const esPdf = archivo.name.toLowerCase().endsWith(".pdf") && (archivo.type === "application/pdf" || archivo.type === "");
  if (!esPdf) return "El enunciado debe ser un archivo PDF (.pdf) con texto seleccionable.";
  if (archivo.size === 0) return "El archivo está vacío.";
  if (archivo.size > MAX_RUBRICA_MB * 1024 * 1024) return `El PDF supera el máximo de ${MAX_RUBRICA_MB} MB.`;
  return undefined;
}

interface SubirRubricaProps {
  labId: number;
  hayContenido: boolean;
  deshabilitado: boolean;
  alCambiarOcupado: (ocupado: boolean) => void;
  alExtraer: (resultado: ResultadoExtraccion) => void;
}

/** Sube el enunciado en PDF y la IA propone la rúbrica (RF-03 CA1). La propuesta no se guarda hasta aprobarla. */
export function SubirRubrica({ labId, hayContenido, deshabilitado, alCambiarOcupado, alExtraer }: SubirRubricaProps) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [extrayendo, setExtrayendo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorArchivo = archivo ? validarArchivoRubrica(archivo) : undefined;

  async function extraer() {
    if (!archivo || errorArchivo) return;
    const mensaje = "La rúbrica extraída reemplazará todo lo que hay ahora en el editor. ¿Deseas continuar?";
    if (hayContenido && !window.confirm(mensaje)) return;
    setError(null);
    setExtrayendo(true);
    alCambiarOcupado(true);
    try {
      alExtraer(await extraerRubrica(labId, archivo));
      setArchivo(null);
    } catch (causa) {
      // 404, 413, 422 y 503 traen `detail` en español: se muestra tal cual.
      setError(mensajeDeError(causa));
    } finally {
      setExtrayendo(false);
      alCambiarOcupado(false);
    }
  }

  return (
    <section aria-labelledby="titulo-subir" className="space-y-3 rounded-xl border p-4">
      <h2 id="titulo-subir" className="font-semibold">
        Extraer la rúbrica con IA
      </h2>
      <CampoArchivo
        id="archivo-rubrica"
        etiqueta="Enunciado del laboratorio (PDF)"
        ayuda={`Solo PDF con texto seleccionable, máximo ${MAX_RUBRICA_MB} MB. La IA propone criterios y niveles que luego revisas antes de aprobar.`}
        accept="application/pdf,.pdf"
        error={errorArchivo}
        deshabilitado={deshabilitado || extrayendo}
        archivos={archivo ? [archivo] : []}
        alElegir={(archivos) => setArchivo(archivos[0] ?? null)}
        alQuitar={() => setArchivo(null)}
      />
      <Button type="button" onClick={() => void extraer()} disabled={!archivo || Boolean(errorArchivo) || deshabilitado || extrayendo}>
        {extrayendo ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Sparkles aria-hidden="true" />}
        {extrayendo ? "Extrayendo con IA…" : "Extraer rúbrica"}
      </Button>
      {extrayendo && <p role="status" className="sr-only">Extrayendo con IA…</p>}
      {error && <Aviso tipo="error" mensaje={error} />}
    </section>
  );
}
