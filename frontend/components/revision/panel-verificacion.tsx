import { Info } from "lucide-react";

/**
 * Aviso de dato que el backend todavía no expone (p. ej. la verificación técnica del código o la respuesta
 * cruda del modelo). No se inventan valores: se explica que no está disponible.
 */
export function NoDisponible({ titulo, mensaje }: { titulo: string; mensaje: string }) {
  return (
    <div role="note" className="flex items-start gap-2 rounded-lg border border-dashed bg-muted/30 p-3 text-sm">
      <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div>
        <p className="font-medium">{titulo}</p>
        <p className="text-muted-foreground">{mensaje}</p>
      </div>
    </div>
  );
}

/** Verificación técnica del código (RF-06): el backend aún no la incluye en la evaluación ni en la traza. */
export function PanelVerificacion() {
  return (
    <NoDisponible
      titulo="Verificación técnica no disponible"
      mensaje="El servidor todavía no envía los resultados del análisis estático ni de las pruebas del código para esta evaluación."
    />
  );
}
