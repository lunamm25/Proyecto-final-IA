import { ChevronDown } from "lucide-react";
import type { CriterioRubrica, NivelDesempeno, RubricaVersion } from "@/lib/tipos";

function formatearNumero(valor: number): string {
  return valor.toLocaleString("es-CO", { maximumFractionDigits: 2 });
}

function ListaNiveles({ niveles }: { niveles: NivelDesempeno[] }) {
  return (
    <ul className="space-y-2">
      {niveles.map((nivel) => (
        <li key={nivel.nombre} className="text-sm">
          <span className="font-medium">{nivel.nombre}</span>
          <span className="text-muted-foreground"> · {formatearNumero(nivel.puntaje)} pts</span>
          <p className="text-muted-foreground">{nivel.descriptor}</p>
        </li>
      ))}
    </ul>
  );
}

function TablaCriterios({ criterios }: { criterios: CriterioRubrica[] }) {
  return (
    <div className="hidden overflow-x-auto rounded-xl border md:block">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Criterios de la rúbrica con su competencia, ponderación y niveles</caption>
        <thead className="bg-muted/60 text-xs uppercase text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3">Criterio</th>
            <th scope="col" className="px-4 py-3">Competencia</th>
            <th scope="col" className="px-4 py-3 text-right">Ponderación</th>
            <th scope="col" className="px-4 py-3">Niveles (nombre, puntaje y descriptor)</th>
          </tr>
        </thead>
        <tbody>
          {criterios.map((criterio) => (
            <tr key={criterio.id} className="border-t align-top">
              <th scope="row" className="px-4 py-3 font-medium">{criterio.nombre}</th>
              <td className="px-4 py-3">{criterio.competencia}</td>
              <td className="px-4 py-3 text-right font-mono">{formatearNumero(criterio.ponderacion)} %</td>
              <td className="px-4 py-3">
                <ListaNiveles niveles={criterio.niveles} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AcordeonCriterios({ criterios }: { criterios: CriterioRubrica[] }) {
  return (
    <div className="space-y-2 md:hidden">
      {criterios.map((criterio) => (
        <details key={criterio.id} className="group rounded-xl border bg-card">
          <summary className="flex cursor-pointer list-none items-start justify-between gap-3 p-4 outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
            <span>
              <span className="block font-medium">{criterio.nombre}</span>
              <span className="block text-xs text-muted-foreground">
                {criterio.competencia} · {formatearNumero(criterio.ponderacion)} %
              </span>
            </span>
            <ChevronDown className="mt-1 size-4 shrink-0 transition-transform group-open:rotate-180" aria-hidden="true" />
          </summary>
          <div className="border-t p-4">
            <ListaNiveles niveles={criterio.niveles} />
          </div>
        </details>
      ))}
    </div>
  );
}

export function VistaRubrica({ rubrica }: { rubrica: RubricaVersion }) {
  return (
    <section aria-labelledby="titulo-rubrica" className="space-y-3">
      <div>
        <h2 id="titulo-rubrica" className="text-xl font-semibold">
          Rúbrica vigente
        </h2>
        <p className="text-sm text-muted-foreground">
          {rubrica.contenido.titulo} · versión {rubrica.version}
        </p>
      </div>
      <TablaCriterios criterios={rubrica.contenido.criterios} />
      <AcordeonCriterios criterios={rubrica.contenido.criterios} />
    </section>
  );
}
