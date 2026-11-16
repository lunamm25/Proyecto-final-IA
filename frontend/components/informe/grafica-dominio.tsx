"use client";

import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import { EstadoVacio } from "@/components/estados";
import { formatearDominio, textoNivel } from "@/components/informe/formato-informe";
import {
  COLOR_PRINCIPAL,
  COLOR_REJILLA,
  ESTILO_EJE,
  ESTILO_TOOLTIP,
  MarcoGrafica,
} from "@/components/informe/marco-grafica";
import { SeccionInforme } from "@/components/informe/seccion-informe";
import type { NivelDominio } from "@/lib/tipos";

const ALTO_POR_BARRA = 40;
const ALTO_EJES = 48;

/** Una competencia o temática del informe: `promedio` de 0 a 5 calculado por el backend. */
export interface DatoDominio {
  nombre: string;
  promedio: number | null;
  nivel_dominio: NivelDominio | null;
  criterios_evaluados: number;
}

interface FilaDominio extends DatoDominio {
  etiqueta: string;
}

/** Añade la etiqueta "3,5 / 5 · Medio" a cada fila (solo formato del dato del backend). */
function filasConEtiqueta(datos: DatoDominio[]): FilaDominio[] {
  return datos.map((d) => ({
    ...d,
    etiqueta: d.promedio === null ? "Sin datos" : `${formatearDominio(d.promedio)} · ${textoNivel(d.nivel_dominio)}`,
  }));
}

function descripcionAccesible(titulo: string, filas: FilaDominio[]): string {
  const detalle = filas.map((f) => `${f.nombre}: ${f.etiqueta}`).join("; ");
  return `Gráfica de barras horizontales: ${titulo.toLowerCase()}, de 0 a 5. ${detalle}.`;
}

function TablaDominio({ filas, columna }: { filas: FilaDominio[]; columna: string }) {
  return (
    <details className="mt-3 text-sm print:hidden">
      <summary className="cursor-pointer font-medium">Ver datos de la gráfica</summary>
      <div className="overflow-x-auto">
        <table className="mt-2 w-full text-left">
          <thead className="text-muted-foreground">
            <tr>
              <th scope="col" className="py-1 pr-4 font-medium">{columna}</th>
              <th scope="col" className="py-1 pr-4 font-medium">Dominio</th>
              <th scope="col" className="py-1 pr-4 font-medium">Nivel</th>
              <th scope="col" className="py-1 font-medium">Criterios evaluados</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.nombre} className="border-t">
                <td className="py-1 pr-4">{f.nombre}</td>
                <td className="py-1 pr-4 tabular-nums">{formatearDominio(f.promedio)}</td>
                <td className="py-1 pr-4">{textoNivel(f.nivel_dominio)}</td>
                <td className="py-1 tabular-nums">{f.criterios_evaluados}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function Grafica({ titulo, filas, imprimiendo }: { titulo: string; filas: FilaDominio[]; imprimiendo: boolean }) {
  return (
    <MarcoGrafica etiqueta={descripcionAccesible(titulo, filas)} alto={filas.length * ALTO_POR_BARRA + ALTO_EJES} imprimiendo={imprimiendo}>
      <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 128, bottom: 8, left: 0 }}>
        <CartesianGrid horizontal={false} stroke={COLOR_REJILLA} />
        <XAxis type="number" domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} tick={ESTILO_EJE} tickLine={false}
          axisLine={{ stroke: COLOR_REJILLA }} />
        <YAxis type="category" dataKey="nombre" width={160} tick={ESTILO_EJE} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={ESTILO_TOOLTIP}
          cursor={{ fill: "var(--muted)" }}
          formatter={(valor) => [typeof valor === "number" ? formatearDominio(valor) : "Sin datos", "Dominio"]}
        />
        <Bar dataKey="promedio" fill={COLOR_PRINCIPAL} radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false}>
          <LabelList dataKey="etiqueta" position="right" style={ESTILO_EJE} />
        </Bar>
      </BarChart>
    </MarcoGrafica>
  );
}

interface GraficaDominioProps {
  id: string;
  titulo: string;
  descripcion: string;
  /** Encabezado de la primera columna de la tabla de datos ("Competencia" o "Temática"). */
  columna: string;
  datos: DatoDominio[];
  imprimiendo: boolean;
}

/** Dominio (0 a 5) y nivel por competencia o temática, tal como los calcula el backend. */
export function GraficaDominio({ id, titulo, descripcion, columna, datos, imprimiendo }: GraficaDominioProps) {
  const filas = filasConEtiqueta(datos);
  return (
    <SeccionInforme id={id} titulo={titulo} descripcion={descripcion} sinCorte>
      {filas.length === 0 ? (
        <EstadoVacio titulo={`Sin datos de ${columna.toLowerCase()}`} />
      ) : (
        <>
          <Grafica titulo={titulo} filas={filas} imprimiendo={imprimiendo} />
          <TablaDominio filas={filas} columna={columna} />
        </>
      )}
    </SeccionInforme>
  );
}
