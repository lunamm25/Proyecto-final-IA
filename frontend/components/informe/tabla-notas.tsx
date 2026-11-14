import Link from "next/link";
import { SeccionInforme } from "@/components/informe/seccion-informe";
import { textoNota } from "@/components/informe/formato-informe";
import { rutaEvaluacion } from "@/lib/rutas-evaluacion";
import type { LaboratorioInforme } from "@/lib/tipos";

/** Notas por laboratorio en el orden que envía el backend, con enlace a cada evaluación publicada. */
export function TablaNotas({ laboratorios }: { laboratorios: LaboratorioInforme[] }) {
  return (
    <SeccionInforme id="titulo-notas" titulo="Notas por laboratorio" sinCorte>
      <div className="overflow-x-auto">
        <table className="w-full min-w-md text-left text-sm">
          <thead className="text-muted-foreground">
            <tr>
              <th scope="col" className="py-2 pr-4 font-medium">Cohorte</th>
              <th scope="col" className="py-2 pr-4 font-medium">Código</th>
              <th scope="col" className="py-2 pr-4 font-medium">Laboratorio</th>
              <th scope="col" className="py-2 text-right font-medium">Nota</th>
            </tr>
          </thead>
          <tbody>
            {laboratorios.map((lab) => (
              <tr key={lab.laboratorio_id} className="border-t break-inside-avoid">
                <td className="py-2 pr-4">{lab.cohorte}</td>
                <td className="py-2 pr-4 font-mono text-xs">{lab.codigo}</td>
                <td className="py-2 pr-4">
                  <Link
                    href={rutaEvaluacion(lab.evaluacion_id, { laboratorioId: lab.laboratorio_id })}
                    className="underline-offset-4 hover:underline print:no-underline"
                  >
                    {lab.titulo}
                  </Link>
                </td>
                <td className="py-2 text-right font-semibold tabular-nums">
                  {textoNota(lab.nota)} {lab.nota !== null && <span className="font-normal text-muted-foreground">/ 5,0</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SeccionInforme>
  );
}
