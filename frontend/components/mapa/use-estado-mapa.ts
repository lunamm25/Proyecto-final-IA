"use client";

import { useCallback, useMemo, useState } from "react";
import {
  NIVELES,
  ancestros,
  filtroActivo,
  idsCoincidentes,
  idsConHijos,
  idsOcultos,
  type Filtro,
  type Jerarquia,
} from "@/components/mapa/grafo-mapa";
import type { NivelMapa } from "@/components/mapa/grafo-mapa";

/** Quita de `colapsados` los ancestros de los ids dados para que queden visibles. */
function expandirAncestros(j: Jerarquia, colapsados: Set<string>, ids: string[]): Set<string> {
  const abrir = new Set(ids.flatMap((id) => ancestros(j, id)));
  if (![...abrir].some((id) => colapsados.has(id))) return colapsados;
  return new Set([...colapsados].filter((id) => !abrir.has(id)));
}

function alternarEnConjunto<T>(conjunto: Set<T>, valor: T): Set<T> {
  const nuevo = new Set(conjunto);
  if (nuevo.has(valor)) nuevo.delete(valor);
  else nuevo.add(valor);
  return nuevo;
}

/** Estado compartido por el grafo y la vista de lista: ramas colapsadas, búsqueda, filtro y selección. */
export function useEstadoMapa(j: Jerarquia) {
  const [colapsados, setColapsados] = useState<Set<string>>(() => new Set());
  const [consulta, setConsulta] = useState("");
  const [niveles, setNiveles] = useState<Set<NivelMapa>>(() => new Set(NIVELES));
  const [seleccionadoId, setSeleccionadoId] = useState<string | null>(null);

  const filtro = useMemo<Filtro>(() => ({ consulta, niveles }), [consulta, niveles]);
  const listaCoincidencias = useMemo(() => idsCoincidentes(j, filtro), [j, filtro]);
  const hayFiltro = filtroActivo(filtro);
  const coincidencias = useMemo(
    () => (hayFiltro ? new Set(listaCoincidencias) : null),
    [hayFiltro, listaCoincidencias],
  );
  const ocultos = useMemo(() => idsOcultos(j, colapsados), [j, colapsados]);

  const alternarRama = useCallback((id: string) => setColapsados((previo) => alternarEnConjunto(previo, id)), []);
  const expandirTodo = useCallback(() => setColapsados(new Set()), []);
  const colapsarTodo = useCallback(() => setColapsados(new Set(idsConHijos(j))), [j]);
  const alternarNivel = useCallback((nivel: NivelMapa) => setNiveles((previo) => alternarEnConjunto(previo, nivel)), []);

  /** Actualiza la búsqueda, expande las ramas con coincidencias y devuelve la primera (o null). */
  const buscar = useCallback(
    (texto: string): string | null => {
      setConsulta(texto);
      if (texto.trim() === "") return null;
      const encontrados = idsCoincidentes(j, { consulta: texto, niveles });
      setColapsados((previo) => expandirAncestros(j, previo, encontrados));
      return encontrados[0] ?? null;
    },
    [j, niveles],
  );

  return {
    colapsados,
    consulta,
    niveles,
    seleccionadoId,
    setSeleccionadoId,
    listaCoincidencias,
    coincidencias,
    hayBusqueda: consulta.trim() !== "",
    ocultos,
    alternarRama,
    expandirTodo,
    colapsarTodo,
    alternarNivel,
    buscar,
  };
}

export type EstadoMapa = ReturnType<typeof useEstadoMapa>;
