import { formatearNumero, sumaEsCorrecta } from "@/lib/inconsistencias-rubrica";
import { cn } from "@/lib/utils";

/** Suma de ponderaciones siempre visible; verde si es 100 %, ámbar si no. */
export function SumaPonderaciones({ suma }: { suma: number }) {
  const correcta = sumaEsCorrecta(suma);
  return (
    <p
      aria-live="polite"
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold",
        correcta ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900",
      )}
    >
      Suma: {formatearNumero(suma)} % de 100 %
      <span className="sr-only">{correcta ? " (correcta)" : " (debe ser 100 %)"}</span>
    </p>
  );
}
