// Descargas del mapa (RF-09 CA5): PNG del grafo visible y JSON exacto recibido del backend.
import { getNodesBounds, getViewportForBounds, type Node } from "@xyflow/react";
import { toPng } from "html-to-image";
import type { Mapa } from "@/lib/tipos";

const MARGEN_PNG = 80;
const MAX_LADO_PNG = 4000;

function descargarUrl(url: string, nombre: string): void {
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
}

/** Descarga exactamente los datos {nodos, aristas} del backend (sin posiciones ni estado de la interfaz). */
export function descargarJson(mapa: Mapa, nombre: string): void {
  const datos: Mapa = { nodos: mapa.nodos, aristas: mapa.aristas };
  const url = URL.createObjectURL(new Blob([JSON.stringify(datos, null, 2)], { type: "application/json" }));
  descargarUrl(url, nombre);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function limitar(valor: number, minimo: number): number {
  return Math.min(Math.max(Math.ceil(valor), minimo), MAX_LADO_PNG);
}

/** Excluye controles, minimapa y paneles de React Flow de la imagen. */
function esExportable(elemento: HTMLElement): boolean {
  const clases = elemento.classList;
  if (!clases) return true;
  return !["react-flow__controls", "react-flow__minimap", "react-flow__panel"].some((c) => clases.contains(c));
}

/**
 * Genera el PNG encuadrando todos los nodos visibles sobre fondo blanco
 * (ejemplo oficial de React Flow con getNodesBounds + getViewportForBounds).
 */
export async function descargarPng(contenedor: HTMLElement, nodos: Node[], nombre: string): Promise<void> {
  const visibles = nodos.filter((nodo) => !nodo.hidden);
  const viewport = contenedor.querySelector<HTMLElement>(".react-flow__viewport");
  if (!viewport || visibles.length === 0) throw new Error("No hay nodos visibles para exportar.");
  const limites = getNodesBounds(visibles);
  const ancho = limitar(limites.width + MARGEN_PNG * 2, 800);
  const alto = limitar(limites.height + MARGEN_PNG * 2, 600);
  const vista = getViewportForBounds(limites, ancho, alto, 0.1, 2, 0.05);
  const url = await toPng(viewport, {
    backgroundColor: "#ffffff",
    width: ancho,
    height: alto,
    filter: esExportable,
    style: { width: `${ancho}px`, height: `${alto}px`, transform: `translate(${vista.x}px, ${vista.y}px) scale(${vista.zoom})` },
  });
  descargarUrl(url, nombre);
}
