import { SeccionInforme } from "@/components/informe/seccion-informe";
import { formatearNota } from "@/components/portafolio/estado-entrega";
import type { NotaLaboratorio } from "@/lib/tipos";

/** Notas por laboratorio en el orden que envía el backend. */
export function TablaNotas({ notas }: { notas: NotaLaboratorio[] }) {
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
            {notas.map((n) => (
              <tr key={n.laboratorio_id} className="border-t break-inside-avoid">
                <td className="py-2 pr-4">{n.cohorte}</td>
                <td className="py-2 pr-4 font-mono text-xs">{n.codigo}</td>
                <td className="py-2 pr-4">{n.titulo}</td>
                <td className="py-2 text-right font-semibold tabular-nums">
                  {formatearNota(n.nota)} <span className="font-normal text-muted-foreground">/ 5,0</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SeccionInforme>
  );
}
