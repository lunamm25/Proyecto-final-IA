"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import { EstadoVacio } from "@/components/estados";
import { formatearDiferencia, textoNota } from "@/components/informe/formato-informe";
import {
  COLOR_PRINCIPAL,
  COLOR_REJILLA,
  COLOR_SECUNDARIO,
  ESTILO_EJE,
  ESTILO_TOOLTIP,
  MarcoGrafica,
} from "@/components/informe/marco-grafica";
import { SeccionInforme } from "@/components/informe/seccion-informe";
import { formatearNota } from "@/components/portafolio/estado-entrega";
import type { Evolucion, NotaLaboratorio } from "@/lib/tipos";

const ALTO_GRAFICA = 280;

function colorDeCohorte(cohorte: number): string {
  return cohorte === 1 ? COLOR_SECUNDARIO : COLOR_PRINCIPAL;
}

function formatearValor(valor: unknown): string {
  return typeof valor === "number" ? formatearNota(valor) : String(valor ?? "");
}

function descripcionAccesible(notas: NotaLaboratorio[], evolucion: Evolucion): string {
  const barras = notas.map((n) => `${n.codigo} (cohorte ${n.cohorte}): ${formatearNota(n.nota)}`).join("; ");
  return (
    `Gráfica de barras de la nota por laboratorio, escala de 0 a 5. ${barras}. ` +
    `Promedio cohorte 1: ${textoNota(evolucion.cohorte_1)}; cohorte 2: ${textoNota(evolucion.cohorte_2)}.`
  );
}

function Leyenda() {
  return (
    <ul className="flex flex-wrap gap-4 text-sm text-muted-foreground" aria-hidden="true">
      {[1, 2].map((cohorte) => (
        <li key={cohorte} className="flex items-center gap-2">
          <span className="size-3 rounded-sm" style={{ backgroundColor: colorDeCohorte(cohorte) }} />
          Cohorte {cohorte}
        </li>
      ))}
    </ul>
  );
}

function ResumenEvolucion({ evolucion }: { evolucion: Evolucion }) {
  return (
    <p className="text-sm">
      Promedio cohorte 1: <strong className="tabular-nums">{textoNota(evolucion.cohorte_1)}</strong>
      {" → "}cohorte 2: <strong className="tabular-nums">{textoNota(evolucion.cohorte_2)}</strong>
      {evolucion.diferencia !== null && (
        <span className="text-muted-foreground"> ({formatearDiferencia(evolucion.diferencia)} puntos)</span>
      )}
    </p>
  );
}

interface GraficaEvolucionProps {
  notas: NotaLaboratorio[];
  evolucion: Evolucion;
  imprimiendo: boolean;
}

function Grafica({ notas, evolucion, imprimiendo }: GraficaEvolucionProps) {
  return (
    <MarcoGrafica etiqueta={descripcionAccesible(notas, evolucion)} alto={ALTO_GRAFICA} imprimiendo={imprimiendo}>
      <BarChart data={notas} margin={{ top: 24, right: 8, bottom: 8, left: 0 }}>
        <CartesianGrid vertical={false} stroke={COLOR_REJILLA} />
        <XAxis dataKey="codigo" tick={ESTILO_EJE} tickLine={false} axisLine={{ stroke: COLOR_REJILLA }} />
        <YAxis
          domain={[0, 5]}
          ticks={[0, 1, 2, 3, 4, 5]}
          tick={ESTILO_EJE}
          tickLine={false}
          axisLine={false}
          width={56}
          label={{ value: "Nota (0–5)", angle: -90, position: "insideLeft", fill: "var(--muted-foreground)", fontSize: 12 }}
        />
        <Tooltip
          contentStyle={ESTILO_TOOLTIP}
          cursor={{ fill: "var(--muted)" }}
          labelFormatter={(codigo) => `Laboratorio ${String(codigo)}`}
          formatter={(valor) => [formatearValor(valor), "Nota"]}
        />
        <Bar dataKey="nota" name="Nota" radius={[4, 4, 0, 0]} maxBarSize={56} isAnimationActive={false}>
          {notas.map((n) => (
            <Cell key={n.laboratorio_id} fill={colorDeCohorte(n.cohorte)} />
          ))}
          <LabelList dataKey="nota" position="top" formatter={formatearValor} style={ESTILO_EJE} />
        </Bar>
      </BarChart>
    </MarcoGrafica>
  );
}

/** Evolución cohorte 1 → cohorte 2: nota de cada laboratorio en el orden en que la envía el backend. */
export function GraficaEvolucion(props: GraficaEvolucionProps) {
  return (
    <SeccionInforme
      id="titulo-evolucion"
      titulo="Evolución cohorte 1 → cohorte 2"
      descripcion="Nota de cada laboratorio evaluado. Los datos están en la tabla «Notas por laboratorio»."
      sinCorte
    >
      {props.notas.length === 0 ? (
        <EstadoVacio titulo="Sin notas para graficar" />
      ) : (
        <div className="space-y-3">
          <ResumenEvolucion evolucion={props.evolucion} />
          <Grafica {...props} />
          <Leyenda />
        </div>
      )}
    </SeccionInforme>
  );
}
