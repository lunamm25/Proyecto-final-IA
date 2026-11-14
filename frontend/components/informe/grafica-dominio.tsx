"use client";

import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import { EstadoVacio } from "@/components/estados";
import { formatearDominio, TEXTO_NIVEL } from "@/components/informe/formato-informe";
import {
  COLOR_PRINCIPAL,
  COLOR_REJILLA,
  ESTILO_EJE,
  ESTILO_TOOLTIP,
  MarcoGrafica,
} from "@/components/informe/marco-grafica";
import { SeccionInforme } from "@/components/informe/seccion-informe";
import type { DominioCompetencia } from "@/lib/tipos";

const ALTO_POR_BARRA = 40;
const ALTO_EJES = 48;

interface FilaDominio extends DominioCompetencia {
  etiqueta: string;
}

/** Añade la etiqueta "70 % · Medio" a cada competencia (solo formato del dato del backend). */
function filasConEtiqueta(dominios: DominioCompetencia[]): FilaDominio[] {
  return dominios.map((d) => ({ ...d, etiqueta: `${formatearDominio(d.dominio)} · ${TEXTO_NIVEL[d.nivel]}` }));
}

function descripcionAccesible(filas: FilaDominio[]): string {
  const detalle = filas.map((f) => `${f.competencia}: ${f.etiqueta}`).join("; ");
  return `Gráfica de barras horizontales del dominio por competencia, de 0 % a 100 %. ${detalle}.`;
}

function TablaDominio({ filas }: { filas: FilaDominio[] }) {
  return (
    <details className="mt-3 text-sm print:hidden">
      <summary className="cursor-pointer font-medium">Ver datos de la gráfica</summary>
      <table className="mt-2 w-full text-left">
        <thead className="text-muted-foreground">
          <tr>
            <th scope="col" className="py-1 pr-4 font-medium">Competencia</th>
            <th scope="col" className="py-1 pr-4 font-medium">Dominio</th>
            <th scope="col" className="py-1 font-medium">Nivel</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <tr key={f.competencia} className="border-t">
              <td className="py-1 pr-4">{f.competencia}</td>
              <td className="py-1 pr-4 tabular-nums">{formatearDominio(f.dominio)}</td>
              <td className="py-1">{TEXTO_NIVEL[f.nivel]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function Grafica({ filas, imprimiendo }: { filas: FilaDominio[]; imprimiendo: boolean }) {
  return (
    <MarcoGrafica
      etiqueta={descripcionAccesible(filas)}
      alto={filas.length * ALTO_POR_BARRA + ALTO_EJES}
      imprimiendo={imprimiendo}
    >
      <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 112, bottom: 8, left: 0 }}>
        <CartesianGrid horizontal={false} stroke={COLOR_REJILLA} />
        <XAxis
          type="number"
          domain={[0, 1]}
          ticks={[0, 0.25, 0.5, 0.75, 1]}
          tickFormatter={(valor: number) => formatearDominio(valor)}
          tick={ESTILO_EJE}
          tickLine={false}
          axisLine={{ stroke: COLOR_REJILLA }}
        />
        <YAxis type="category" dataKey="competencia" width={160} tick={ESTILO_EJE} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={ESTILO_TOOLTIP}
          cursor={{ fill: "var(--muted)" }}
          formatter={(valor) => [typeof valor === "number" ? formatearDominio(valor) : String(valor ?? ""), "Dominio"]}
        />
        <Bar dataKey="dominio" fill={COLOR_PRINCIPAL} radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false}>
          <LabelList dataKey="etiqueta" position="right" style={ESTILO_EJE} />
        </Bar>
      </BarChart>
    </MarcoGrafica>
  );
}

interface GraficaDominioProps {
  dominios: DominioCompetencia[];
  imprimiendo: boolean;
}

/** Nivel de dominio por competencia (0 a 1) tal como lo calcula el backend. */
export function GraficaDominio({ dominios, imprimiendo }: GraficaDominioProps) {
  const filas = filasConEtiqueta(dominios);
  return (
    <SeccionInforme
      id="titulo-dominio"
      titulo="Dominio por competencia"
      descripcion="Porcentaje de dominio y nivel en cada competencia evaluada."
      sinCorte
    >
      {filas.length === 0 ? (
        <EstadoVacio titulo="Sin competencias evaluadas" />
      ) : (
        <>
          <Grafica filas={filas} imprimiendo={imprimiendo} />
          <TablaDominio filas={filas} />
        </>
      )}
    </SeccionInforme>
  );
}
