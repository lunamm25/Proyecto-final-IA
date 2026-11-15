import { CheckCircle2, Info, XCircle } from "lucide-react";
import type { VerificacionResumen } from "@/lib/tipos";

/**
 * Aviso de dato que el backend no envió (p. ej. la verificación técnica cuando el código no se ejecutó, o la respuesta
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

function SiNo({ valor, textoSi, textoNo, siEsBueno }: { valor: boolean; textoSi: string; textoNo: string; siEsBueno: boolean }) {
  const bueno = valor === siEsBueno;
  const Icono = bueno ? CheckCircle2 : XCircle;
  return (
    <span className={`inline-flex items-center gap-1 font-medium ${bueno ? "text-emerald-800" : "text-destructive"}`}>
      <Icono className="size-4" aria-hidden="true" />
      {valor ? textoSi : textoNo}
    </span>
  );
}

/**
 * Verificación técnica del código (RF-06): VerificacionResumen del backend, el resumen de la ejecución en el sandbox
 * (nunca stdout ni stderr). Si no viene (no se ejecutó el código), muestra "no disponible".
 */
export function PanelVerificacion({ verificacion }: { verificacion: VerificacionResumen | null | undefined }) {
  if (!verificacion) {
    return (
      <NoDisponible
        titulo="Verificación técnica no disponible"
        mensaje="El código de esta entrega no se ejecutó en el sandbox (por ejemplo, porque no se adjuntó un ZIP)."
      />
    );
  }
  const exitosa = verificacion.ejecucion_exitosa;
  return (
    <div className={`rounded-lg border p-3 text-sm ${exitosa ? "border-emerald-300 bg-emerald-50/60" : "border-destructive/30 bg-destructive/5"}`}>
      <p className="font-medium">{exitosa ? "El código se ejecutó correctamente en el sandbox." : "La ejecución del código en el sandbox falló."}</p>
      <dl className="mt-2 grid gap-x-6 gap-y-1.5 sm:grid-cols-[auto_1fr]">
        <dt className="text-muted-foreground">Ejecución</dt>
        <dd><SiNo valor={exitosa} textoSi="Exitosa" textoNo="Fallida" siEsBueno /></dd>
        <dt className="text-muted-foreground">Errores</dt>
        <dd><SiNo valor={verificacion.tiene_error} textoSi="Hubo errores" textoNo="Sin errores" siEsBueno={false} /></dd>
        <dt className="text-muted-foreground">Código de salida</dt>
        <dd className="font-mono">{verificacion.codigo_salida}</dd>
      </dl>
      <p className="mt-2 text-xs text-muted-foreground">
        Por seguridad, el servidor no muestra la salida del programa; solo este resumen.
      </p>
    </div>
  );
}
