import { promedioDeCohorte, textoNota } from "@/components/informe/formato-informe";
import type { Informe } from "@/lib/tipos";

interface TarjetaKpiProps {
  titulo: string;
  valor: string;
  unidad?: string;
}

function TarjetaKpi({ titulo, valor, unidad }: TarjetaKpiProps) {
  return (
    <div className="rounded-xl border bg-card p-4 break-inside-avoid">
      <dt className="text-sm text-muted-foreground">{titulo}</dt>
      <dd className="mt-1 text-2xl font-bold tabular-nums">
        {valor}
        {unidad && <span className="ml-1 text-sm font-normal text-muted-foreground">{unidad}</span>}
      </dd>
    </div>
  );
}

function unidadNota(valor: number | null): TarjetaKpiProps["unidad"] {
  return valor === null ? undefined : "/ 5,0";
}

/** KPIs del informe. Todos los valores vienen calculados por el backend. */
export function TarjetasKpi({ informe }: { informe: Informe }) {
  const general = informe.promedio_general;
  const cohorte1 = promedioDeCohorte(informe.promedios_cohorte, 1);
  const cohorte2 = promedioDeCohorte(informe.promedios_cohorte, 2);
  return (
    <section aria-labelledby="titulo-kpis">
      <h2 id="titulo-kpis" className="sr-only">Indicadores principales</h2>
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4 print:grid-cols-4">
        <TarjetaKpi titulo="Promedio general" valor={textoNota(general)} unidad={unidadNota(general)} />
        <TarjetaKpi titulo="Promedio cohorte 1" valor={textoNota(cohorte1)} unidad={unidadNota(cohorte1)} />
        <TarjetaKpi titulo="Promedio cohorte 2" valor={textoNota(cohorte2)} unidad={unidadNota(cohorte2)} />
        <TarjetaKpi titulo="Laboratorios evaluados" valor={String(informe.notas_laboratorio.length)} />
      </dl>
    </section>
  );
}
