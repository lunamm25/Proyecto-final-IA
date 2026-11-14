"use client";

import { cn } from "@/lib/utils";

export const CLASE_CONTROL =
  "w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive disabled:cursor-not-allowed disabled:opacity-50";

interface CampoProps {
  id: string;
  etiqueta: string;
  obligatorio?: boolean;
  ayuda?: string;
  error?: string;
  className?: string;
  /** Recibe los atributos de accesibilidad que debe llevar el control. */
  children: (accesibilidad: AtributosControl) => React.ReactNode;
}

export interface AtributosControl {
  id: string;
  "aria-invalid": true | undefined;
  "aria-describedby": string | undefined;
  "aria-required": true | undefined;
}

/** Etiqueta + control + ayuda + error, con aria-invalid y aria-describedby ya conectados. */
export function Campo({ id, etiqueta, obligatorio = false, ayuda, error, className, children }: CampoProps) {
  const descripciones = [ayuda ? `${id}-ayuda` : null, error ? `${id}-error` : null].filter(Boolean);
  return (
    <div className={cn("space-y-1", className)}>
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
        {obligatorio && <span className="text-destructive"> *</span>}
      </label>
      {children({
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": descripciones.length > 0 ? descripciones.join(" ") : undefined,
        "aria-required": obligatorio ? true : undefined,
      })}
      {ayuda && (
        <p id={`${id}-ayuda`} className="text-xs text-muted-foreground">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
