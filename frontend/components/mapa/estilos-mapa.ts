// Estilos del mapa mental: color + texto + icono por nivel (no depende solo del color) y forma por tipo.
import { BookOpen, CircleCheck, CircleDashed, CircleDot, FlaskConical, Lightbulb, TriangleAlert, type LucideIcon } from "lucide-react";
import type { NivelDominio, TipoNodo } from "@/lib/tipos";

interface EstiloNivel {
  etiqueta: string;
  descripcion: string;
  Icono: LucideIcon;
  /** Borde y fondo suave del nodo. */
  claseNodo: string;
  /** Insignia con el nombre del nivel. */
  claseInsignia: string;
  /** Color para el MiniMap (variable CSS del tema). */
  colorMini: string;
}

export const ESTILO_NIVEL: Record<NivelDominio, EstiloNivel> = {
  alto: {
    etiqueta: "Alto",
    descripcion: "Dominio alto",
    Icono: CircleCheck,
    claseNodo: "border-nivel-alto bg-nivel-alto-fondo",
    claseInsignia: "bg-nivel-alto text-nivel-alto-texto",
    colorMini: "var(--nivel-alto)",
  },
  medio: {
    etiqueta: "Medio",
    descripcion: "Dominio medio",
    Icono: CircleDot,
    claseNodo: "border-nivel-medio bg-nivel-medio-fondo",
    claseInsignia: "bg-nivel-medio text-nivel-medio-texto",
    colorMini: "var(--nivel-medio)",
  },
  bajo: {
    etiqueta: "Bajo",
    descripcion: "Dominio bajo",
    Icono: TriangleAlert,
    claseNodo: "border-nivel-bajo bg-nivel-bajo-fondo",
    claseInsignia: "bg-nivel-bajo text-nivel-bajo-texto",
    colorMini: "var(--nivel-bajo)",
  },
  sin_evidencia: {
    etiqueta: "Sin evidencia",
    descripcion: "Sin evidencia en evaluaciones publicadas",
    Icono: CircleDashed,
    claseNodo: "border-dashed border-nivel-sin bg-nivel-sin-fondo",
    claseInsignia: "bg-nivel-sin text-nivel-sin-texto",
    colorMini: "var(--nivel-sin)",
  },
};

interface EstiloTipo {
  etiqueta: string;
  Icono: LucideIcon;
  /** Forma y tamaño del nodo en el grafo. */
  claseForma: string;
  claseTexto: string;
}

export const ESTILO_TIPO: Record<TipoNodo, EstiloTipo> = {
  tematica: { etiqueta: "Temática", Icono: BookOpen, claseForma: "rounded-2xl border-[3px] p-3", claseTexto: "text-base font-bold" },
  concepto: { etiqueta: "Concepto", Icono: Lightbulb, claseForma: "rounded-xl border-2 p-2.5", claseTexto: "text-sm font-semibold" },
  laboratorio: { etiqueta: "Laboratorio", Icono: FlaskConical, claseForma: "rounded-md border p-2", claseTexto: "text-xs font-medium" },
};

/** "0,85" → "85 %"; null → texto de no disponible. */
export function formatearDominio(dominio: number | null): string {
  if (dominio === null) return "Sin dato";
  return `${Math.round(dominio * 100)} %`;
}
