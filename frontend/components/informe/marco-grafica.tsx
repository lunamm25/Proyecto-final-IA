"use client";

import type { CSSProperties, ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

/** Ancho útil de una hoja A4 con márgenes de 15 mm (≈ 180 mm a 96 ppp). */
const ANCHO_IMPRESION = 680;

/** Colores del tema (globals.css): funcionan en claro, oscuro e impresión. */
export const COLOR_PRINCIPAL = "var(--primary)";
export const COLOR_SECUNDARIO = "var(--chart-2)";
export const COLOR_REJILLA = "var(--border)";
export const COLOR_TEXTO_EJE = "var(--muted-foreground)";

export const ESTILO_TOOLTIP: CSSProperties = {
  backgroundColor: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--popover-foreground)",
  fontSize: 13,
};

export const ESTILO_EJE = { fill: COLOR_TEXTO_EJE, fontSize: 12 };

interface MarcoGraficaProps {
  /** Resumen accesible del dato que muestra la gráfica. */
  etiqueta: string;
  alto: number;
  imprimiendo: boolean;
  children: ReactNode;
}

/** Contenedor de gráfica: ancho fluido en pantalla y fijo al imprimir, con descripción accesible. */
export function MarcoGrafica({ etiqueta, alto, imprimiendo, children }: MarcoGraficaProps) {
  return (
    <div role="img" aria-label={etiqueta} className="w-full break-inside-avoid">
      <ResponsiveContainer width={imprimiendo ? ANCHO_IMPRESION : "100%"} height={alto}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}
