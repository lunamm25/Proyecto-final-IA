"use client";

import { useState } from "react";
import {
  mover,
  nuevoCriterio,
  quitar,
  reemplazar,
  rubricaAEditor,
  type CriterioEditor,
  type RubricaEditor,
} from "@/components/rubricas/modelo-editor";
import type { ResultadoServidor } from "@/components/rubricas/resumen-inconsistencias";
import type { Rubrica } from "@/lib/tipos";

/** Estado del borrador: cualquier edición lo marca como "sin guardar" y descarta el resultado del servidor. */
export function useEditorRubrica(inicial: () => RubricaEditor) {
  const [borrador, setBorrador] = useState<RubricaEditor>(inicial);
  const [sucio, setSucio] = useState(false);
  const [servidor, setServidor] = useState<ResultadoServidor | null>(null);

  function editar(cambio: (previo: RubricaEditor) => RubricaEditor) {
    setBorrador(cambio);
    setSucio(true);
    setServidor(null);
  }

  function editarCriterios(cambio: (criterios: CriterioEditor[]) => CriterioEditor[]) {
    editar((previo) => ({ ...previo, criterios: cambio(previo.criterios) }));
  }

  return {
    borrador,
    sucio,
    servidor,
    setServidor,
    cambiarTitulo: (titulo: string) => editar((previo) => ({ ...previo, titulo })),
    agregarCriterio: () => editarCriterios((lista) => [...lista, nuevoCriterio(lista)]),
    cambiarCriterio: (indice: number, cambios: Partial<CriterioEditor>) =>
      editarCriterios((lista) => reemplazar(lista, indice, { ...lista[indice], ...cambios })),
    moverCriterio: (indice: number, delta: number) => editarCriterios((lista) => mover(lista, indice, delta)),
    eliminarCriterio: (indice: number) => editarCriterios((lista) => quitar(lista, indice)),
    /** Carga una rúbrica extraída: queda como cambio sin guardar. */
    cargarExtraida: (rubrica: Rubrica, resultado: ResultadoServidor) => {
      setBorrador(rubricaAEditor(rubrica));
      setSucio(true);
      setServidor(resultado);
    },
    /** Tras guardar, el borrador pasa a ser la versión aprobada. */
    marcarGuardado: (rubrica: Rubrica) => {
      setBorrador(rubricaAEditor(rubrica));
      setSucio(false);
      setServidor(null);
    },
  };
}
