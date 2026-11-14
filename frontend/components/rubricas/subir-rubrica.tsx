"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Aviso } from "@/components/docente/aviso";
import { CampoArchivo } from "@/components/portafolio/campo-archivo";
import { extraerRubrica, mensajeDeError } from "@/lib/api";
import type { ResultadoExtraccion } from "@/lib/tipos";

export const MAX_RUBRICA_MB = 10;
export const EXTENSIONES_RUBRICA = [".pdf", ".docx", ".txt", ".md"];

/** Valida extensión y tamaño en el cliente; el backend vuelve a validar. */
export function validarArchivoRubrica(archivo: File): string | undefined {
  const nombre = archivo.name.toLowerCase();
  if (!EXTENSIONES_RUBRICA.some((ext) => nombre.endsWith(ext))) {
    return "El archivo debe ser PDF, DOCX, TXT o MD.";
  }
  if (archivo.size === 0) return "El archivo está vacío.";
  if (archivo.size > MAX_RUBRICA_MB * 1024 * 1024) return `El archivo supera el máximo de ${MAX_RUBRICA_MB} MB.`;
  return undefined;
}

interface SubirRubricaProps {
  labId: string;
  hayContenido: boolean;
  deshabilitado: boolean;
  alCambiarOcupado: (ocupado: boolean) => void;
  alExtraer: (resultado: ResultadoExtraccion) => void;
}

/** Sube un archivo de rúbrica y lo convierte con IA a `RubricaSchema` (RF-03 CA1). */
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
      setError(mensajeDeError(causa));
    } finally {
      setExtrayendo(false);
      alCambiarOcupado(false);
    }
  }

  return (
    <section aria-labelledby="titulo-subir" className="space-y-3 rounded-xl border p-4">
      <h2 id="titulo-subir" className="font-semibold">
        Subir rúbrica con IA
      </h2>
      <CampoArchivo
        id="archivo-rubrica"
        etiqueta="Archivo de la rúbrica"
        ayuda={`PDF, DOCX, TXT o MD, máximo ${MAX_RUBRICA_MB} MB. La IA la convierte en criterios y niveles que luego puedes revisar.`}
        accept={EXTENSIONES_RUBRICA.join(",")}
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
