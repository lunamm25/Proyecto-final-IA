import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Cargando({ texto = "Cargando…" }: { texto?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
      <Loader2 className="size-5 animate-spin" aria-hidden="true" />
      <span>{texto}</span>
    </div>
  );
}

interface MensajeErrorProps {
  titulo?: string;
  mensaje: string;
  alReintentar?: () => void;
  children?: React.ReactNode;
}

export function MensajeError({ titulo = "Algo salió mal", mensaje, alReintentar, children }: MensajeErrorProps) {
  return (
    <div role="alert" className="mx-auto my-12 max-w-lg rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center">
      <AlertTriangle className="mx-auto size-8 text-destructive" aria-hidden="true" />
      <h2 className="mt-3 text-lg font-semibold">{titulo}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{mensaje}</p>
      {alReintentar && (
        <Button variant="outline" className="mt-4" onClick={alReintentar}>
          Reintentar
        </Button>
      )}
      {children}
    </div>
  );
}

export function EstadoVacio({ titulo, mensaje }: { titulo: string; mensaje?: string }) {
  return (
    <div className="mx-auto my-12 max-w-lg rounded-xl border border-dashed p-6 text-center">
      <Inbox className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
      <h2 className="mt-3 text-lg font-semibold">{titulo}</h2>
      {mensaje && <p className="mt-2 text-sm text-muted-foreground">{mensaje}</p>}
    </div>
  );
}
