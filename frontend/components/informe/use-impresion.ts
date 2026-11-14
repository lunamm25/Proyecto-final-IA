"use client";

import { useEffect, useState } from "react";
import { flushSync } from "react-dom";

/**
 * Indica si el navegador está preparando la impresión. Se actualiza de forma síncrona en
 * `beforeprint` para que las gráficas se dibujen con ancho fijo antes de generar el PDF
 * (también al usar Ctrl+P).
 */
export function useModoImpresion(): boolean {
  const [imprimiendo, setImprimiendo] = useState(false);

  useEffect(() => {
    const antes = () => flushSync(() => setImprimiendo(true));
    const despues = () => setImprimiendo(false);
    window.addEventListener("beforeprint", antes);
    window.addEventListener("afterprint", despues);
    return () => {
      window.removeEventListener("beforeprint", antes);
      window.removeEventListener("afterprint", despues);
    };
  }, []);

  return imprimiendo;
}

/** Abre el diálogo de impresión con un título de documento que da nombre al PDF. */
export function imprimirInforme(nombreEstudiante: string): void {
  const tituloAnterior = document.title;
  document.title = `Informe – ${nombreEstudiante}`;
  window.addEventListener("afterprint", () => (document.title = tituloAnterior), { once: true });
  window.print();
}
