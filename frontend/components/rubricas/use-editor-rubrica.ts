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
  /**
   * true si la última extracción llegó con valida: false. No se borra al editar: solo cuando el servidor valida la
   * rúbrica (Validar con el servidor → valida: true), al cargar una extracción válida o al guardar.
   */
  const [revisionPendiente, setRevisionPendiente] = useState(false);

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
    revisionPendiente,
    /** Llamar cuando "Validar con el servidor" responde valida: true. */
    marcarValidadaPorServidor: () => setRevisionPendiente(false),
    cambiarTitulo: (titulo: string) => editar((previo) => ({ ...previo, titulo })),
    agregarCriterio: () => editarCriterios((lista) => [...lista, nuevoCriterio(lista)]),
    cambiarCriterio: (indice: number, cambios: Partial<CriterioEditor>) =>
      editarCriterios((lista) => reemplazar(lista, indice, { ...lista[indice], ...cambios })),
    moverCriterio: (indice: number, delta: number) => editarCriterios((lista) => mover(lista, indice, delta)),
    eliminarCriterio: (indice: number) => editarCriterios((lista) => quitar(lista, indice)),
    /** Carga una rúbrica extraída (sin guardar). Si el validador del backend dijo valida: false, bloquea el guardado. */
    cargarExtraida: (rubrica: Rubrica, resultado: ResultadoServidor, valida: boolean) => {
      setBorrador(rubricaAEditor(rubrica));
      setSucio(true);
      setServidor(resultado);
      setRevisionPendiente(!valida);
    },
    /** Tras guardar, el borrador pasa a ser la versión aprobada. */
    marcarGuardado: (rubrica: Rubrica) => {
      setBorrador(rubricaAEditor(rubrica));
      setSucio(false);
      setServidor(null);
      setRevisionPendiente(false);
    },
  };
}
