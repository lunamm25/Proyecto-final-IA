import { promedioDeCohorte, textoNota } from "@/components/informe/formato-informe";
import type { Informe } from "@/lib/tipos";

interface TarjetaKpiProps {
  titulo: string;
  valor: string;
  unidad?: string;
  detalle?: string;
}

function TarjetaKpi({ titulo, valor, unidad, detalle }: TarjetaKpiProps) {
  return (
    <div className="rounded-xl border bg-card p-4 break-inside-avoid">
      <dt className="text-sm text-muted-foreground">{titulo}</dt>
      <dd className="mt-1 text-2xl font-bold tabular-nums">
        {valor}
        {unidad && <span className="ml-1 text-sm font-normal text-muted-foreground">{unidad}</span>}
      </dd>
      {detalle && <dd className="mt-1 text-xs text-muted-foreground">{detalle}</dd>}
    </div>
  );
}

function unidadNota(valor: number | null): string | undefined {
  return valor === null ? undefined : "/ 5,0";
}

function TarjetaCohorte({ informe, numero }: { informe: Informe; numero: number }) {
  const cohorte = promedioDeCohorte(informe.promedios_cohorte, numero);
  const promedio = cohorte?.promedio ?? null;
  const evaluados = cohorte?.laboratorios_evaluados ?? 0;
  return (
    <TarjetaKpi
      titulo={`Promedio ${cohorte?.cohorte ?? `cohorte ${numero}`}`}
      valor={textoNota(promedio)}
      unidad={unidadNota(promedio)}
      detalle={evaluados === 1 ? "1 laboratorio evaluado" : `${evaluados} laboratorios evaluados`}
    />
  );
}

/** KPIs del informe. Todos los valores (incluido «laboratorios evaluados») vienen calculados por el backend. */
export function TarjetasKpi({ informe }: { informe: Informe }) {
  const general = informe.promedio_general;
  return (
    <section aria-labelledby="titulo-kpis">
      <h2 id="titulo-kpis" className="sr-only">Indicadores principales</h2>
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4 print:grid-cols-4">
        <TarjetaKpi titulo="Promedio general" valor={textoNota(general)} unidad={unidadNota(general)} />
        <TarjetaCohorte informe={informe} numero={1} />
        <TarjetaCohorte informe={informe} numero={2} />
        <TarjetaKpi titulo="Laboratorios evaluados" valor={String(informe.laboratorios_evaluados)} />
      </dl>
    </section>
  );
}
