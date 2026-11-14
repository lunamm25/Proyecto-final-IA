"use client";

import { FileText, X } from "lucide-react";
import { formatearTamano } from "@/components/portafolio/validacion-entrega";

interface ArchivoElegidoProps {
  archivo: File;
  deshabilitado: boolean;
  alQuitar: () => void;
}

export function ArchivoElegido({ archivo, deshabilitado, alQuitar }: ArchivoElegidoProps) {
  return (
    <li className="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-sm">
      <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate" title={archivo.name}>
        {archivo.name}
      </span>
      <span className="shrink-0 text-xs text-muted-foreground">{formatearTamano(archivo.size)}</span>
      <button
        type="button"
        onClick={alQuitar}
        disabled={deshabilitado}
        aria-label={`Quitar ${archivo.name}`}
        className="rounded p-1 text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
      >
        <X className="size-4" aria-hidden="true" />
      </button>
    </li>
  );
}

interface CampoArchivoProps {
  id: string;
  etiqueta: string;
  ayuda: string;
  accept: string;
  multiple?: boolean;
  obligatorio?: boolean;
  error?: string;
  deshabilitado: boolean;
  /** Deshabilita solo el selector (p. ej. al llegar al máximo de archivos); se pueden seguir quitando. */
  limiteAlcanzado?: boolean;
  archivos: File[];
  alElegir: (archivos: File[]) => void;
  alQuitar: (indice: number) => void;
}

/** Campo de archivo accesible: etiqueta, ayuda, error asociado y lista de archivos elegidos. */
export function CampoArchivo({
  id,
  etiqueta,
  ayuda,
  accept,
  multiple = false,
  obligatorio = false,
  error,
  deshabilitado,
  limiteAlcanzado = false,
  archivos,
  alElegir,
  alQuitar,
}: CampoArchivoProps) {
  const descripcion = error ? `${id}-ayuda ${id}-error` : `${id}-ayuda`;
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
        {obligatorio && <span className="text-destructive"> *</span>}
      </label>
      <p id={`${id}-ayuda`} className="text-xs text-muted-foreground">
        {ayuda}
      </p>
      <input
        id={id}
        name={id}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={deshabilitado || limiteAlcanzado}
        aria-required={obligatorio || undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={descripcion}
        onChange={(evento) => {
          alElegir(Array.from(evento.target.files ?? []));
          evento.target.value = "";
        }}
        className="block w-full cursor-pointer rounded-lg border bg-background text-sm outline-none file:mr-3 file:cursor-pointer file:border-0 file:border-r file:bg-muted file:px-3 file:py-2 file:text-sm file:font-medium focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive disabled:cursor-not-allowed disabled:opacity-50"
      />
      {archivos.length > 0 && (
        <ul className="space-y-1" aria-label={`Archivos elegidos para ${etiqueta}`}>
          {archivos.map((archivo, indice) => (
            <ArchivoElegido
              key={`${archivo.name}-${indice}`}
              archivo={archivo}
              deshabilitado={deshabilitado}
              alQuitar={() => alQuitar(indice)}
            />
          ))}
        </ul>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
