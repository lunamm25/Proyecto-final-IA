"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ESTILO_NIVEL, ESTILO_TIPO, formatearDominio } from "@/components/mapa/estilos-mapa";
import { textoFuente } from "@/components/evaluaciones/estado-evaluacion";
import { nivelDe, type Jerarquia } from "@/components/mapa/grafo-mapa";
import type { EvidenciaMapa, NodoMapa } from "@/lib/tipos";
import { cn } from "@/lib/utils";

interface PropsPanel {
  nodo: NodoMapa;
  jerarquia: Jerarquia;
  alCerrar: () => void;
  alAbrir: (id: string) => void;
}

function ListaTexto({ titulo, elementos, vacio }: { titulo: string; elementos: string[]; vacio: string }) {
  return (
    <section className="space-y-1.5">
      <h3 className="text-sm font-semibold">{titulo}</h3>
      {elementos.length === 0 ? (
        <p className="text-sm text-muted-foreground">{vacio}</p>
      ) : (
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {elementos.map((texto, i) => (
            <li key={`${i}-${texto}`}>{texto}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Evidencias del mapa: citas ya verificadas por el backend (no traen similitud). */
function ListaEvidencias({ evidencias }: { evidencias: EvidenciaMapa[] }) {
  return (
    <section className="space-y-1.5">
      <h3 className="text-sm font-semibold">Evidencias</h3>
      {evidencias.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin evidencias registradas.</p>
      ) : (
        <ul className="space-y-2">
          {evidencias.map((evidencia, i) => (
            <li key={`${i}-${evidencia.laboratorio}-${evidencia.criterio_id}`} className="rounded-lg border bg-muted/30 p-2.5 text-sm">
              <blockquote className="border-l-2 pl-2 italic break-words">“{evidencia.fragmento}”</blockquote>
              <p className="mt-1 text-xs text-muted-foreground">
                {[evidencia.laboratorio, `criterio ${evidencia.criterio_id}`, textoFuente(evidencia.fuente), evidencia.ubicacion]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Nodos unidos por aristas que no forman parte del árbol (relaciones transversales). */
function relacionadosTransversales(jerarquia: Jerarquia, id: string): string[] {
  const padre = jerarquia.padreDe.get(id);
  const hijos = new Set(jerarquia.hijos.get(id) ?? []);
  const otros = jerarquia.aristas.flatMap(({ origen, destino }) => {
    if (origen === id && !hijos.has(destino)) return [destino];
    if (destino === id && origen !== padre) return [origen];
    return [];
  });
  return [...new Set(otros)];
}

function Relacionados({ titulo, ids, jerarquia, alAbrir }: { titulo: string; ids: string[]; jerarquia: Jerarquia; alAbrir: (id: string) => void }) {
  if (ids.length === 0) return null;
  return (
    <section className="space-y-1.5">
      <h3 className="text-sm font-semibold">{titulo}</h3>
      <ul className="flex flex-wrap gap-1.5">
        {ids.map((id) => {
          const relacionado = jerarquia.porId.get(id);
          if (!relacionado) return null;
          return (
            <li key={id}>
              <Button variant="outline" size="sm" onClick={() => alAbrir(id)}>
                {relacionado.etiqueta}
              </Button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Resumen({ nodo }: { nodo: NodoMapa }) {
  const nivel = ESTILO_NIVEL[nivelDe(nodo)];
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-sm">
      <dt className="text-muted-foreground">Tipo</dt>
      <dd>{ESTILO_TIPO[nodo.tipo].etiqueta}</dd>
      <dt className="text-muted-foreground">Nivel de dominio</dt>
      <dd>
        <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold", nivel.claseInsignia)}>
          <nivel.Icono className="size-3.5" aria-hidden="true" />
          {nivel.etiqueta}
        </span>
      </dd>
      <dt className="text-muted-foreground">{nodo.tipo === "laboratorio" ? "Nota" : "Dominio"}</dt>
      <dd>{formatearDominio(nodo.dominio)}</dd>
    </dl>
  );
}

/** Cierra con Escape y devuelve el foco al título cada vez que cambia el nodo mostrado. */
function useFocoPanel(nodoId: string, alCerrar: () => void) {
  const tituloRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    tituloRef.current?.focus();
  }, [nodoId]);
  useEffect(() => {
    const alPresionar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") alCerrar();
    };
    document.addEventListener("keydown", alPresionar);
    return () => document.removeEventListener("keydown", alPresionar);
  }, [alCerrar]);
  return tituloRef;
}

/** Panel con el detalle del nodo: lateral en escritorio y hoja inferior en móvil. */
export function PanelDetalle({ nodo, jerarquia, alCerrar, alAbrir }: PropsPanel) {
  const tituloRef = useFocoPanel(nodo.id, alCerrar);
  const padre = jerarquia.padreDe.get(nodo.id);
  return (
    <aside
      role="dialog"
      aria-modal="false"
      aria-labelledby="titulo-detalle-nodo"
      className="fixed inset-x-0 bottom-0 z-50 max-h-[80svh] overflow-y-auto rounded-t-2xl border bg-background p-4 shadow-2xl lg:static lg:z-auto lg:max-h-[calc(100svh-15rem)] lg:min-h-[520px] lg:w-96 lg:shrink-0 lg:rounded-xl lg:shadow-none"
    >
      <div className="flex items-start justify-between gap-2">
        <h2 id="titulo-detalle-nodo" ref={tituloRef} tabIndex={-1} className="text-lg font-semibold focus:outline-none">
          {nodo.etiqueta}
        </h2>
        <Button variant="ghost" size="icon" onClick={alCerrar} aria-label="Cerrar detalle">
          <X aria-hidden="true" />
        </Button>
      </div>
      <div className="mt-3 space-y-4">
        <Resumen nodo={nodo} />
        <ListaTexto titulo="Laboratorios donde se aplicó" elementos={nodo.laboratorios} vacio="Aún no se ha aplicado en laboratorios con evaluación publicada." />
        <ListaEvidencias evidencias={nodo.evidencias} />
        <ListaTexto titulo="Aspectos por profundizar" elementos={nodo.aspectos_por_profundizar} vacio="No hay aspectos pendientes registrados." />
        <Relacionados titulo="Pertenece a" ids={padre ? [padre] : []} jerarquia={jerarquia} alAbrir={alAbrir} />
        <Relacionados titulo="Contiene" ids={jerarquia.hijos.get(nodo.id) ?? []} jerarquia={jerarquia} alAbrir={alAbrir} />
        <Relacionados titulo="Relacionado con" ids={relacionadosTransversales(jerarquia, nodo.id)} jerarquia={jerarquia} alAbrir={alAbrir} />
      </div>
    </aside>
  );
}
