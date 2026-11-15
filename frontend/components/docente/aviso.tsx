import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

export type TipoAviso = "exito" | "error" | "info";

export interface DatosAviso {
  tipo: TipoAviso;
  mensaje: string;
}

const ESTILOS: Record<TipoAviso, string> = {
  exito: "border-emerald-300 bg-emerald-50 text-emerald-900",
  error: "border-destructive/30 bg-destructive/5 text-destructive",
  info: "border-sky-300 bg-sky-50 text-sky-900",
};

const ICONOS = { exito: CheckCircle2, error: AlertTriangle, info: Info } as const;

/** Mensaje en línea; los errores se anuncian como alerta y el resto como estado. */
export function Aviso({ tipo, mensaje, className }: DatosAviso & { className?: string }) {
  const Icono = ICONOS[tipo];
  return (
    <div
      role={tipo === "error" ? "alert" : "status"}
      className={cn("flex items-start gap-2 rounded-lg border p-3 text-sm", ESTILOS[tipo], className)}
    >
      <Icono className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p>{mensaje}</p>
    </div>
  );
}
