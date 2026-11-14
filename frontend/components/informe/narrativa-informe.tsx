import { PlanFortalecimiento } from "@/components/informe/plan-fortalecimiento";
import { SeccionInforme } from "@/components/informe/seccion-informe";
import type { InformeNarrativo } from "@/lib/tipos";

function ListaTextos({ textos, vacio }: { textos: string[]; vacio: string }) {
  if (textos.length === 0) return <p className="text-sm text-muted-foreground">{vacio}</p>;
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm">
      {textos.map((texto, indice) => (
        <li key={indice}>{texto}</li>
      ))}
    </ul>
  );
}

/** Narrativa del informe (InformeNarrativoSchema §7). Si aún no existe, lo indica sin romper la vista. */
export function NarrativaInforme({ narrativa }: { narrativa: InformeNarrativo | null }) {
  if (!narrativa) {
    return (
      <SeccionInforme id="titulo-narrativa" titulo="Análisis del aprendizaje" sinCorte>
        <p className="text-sm text-muted-foreground">
          El análisis narrativo (competencias, brechas y plan de fortalecimiento) aún no está disponible.
        </p>
      </SeccionInforme>
    );
  }
  return (
    <>
      <div className="grid gap-6 md:grid-cols-2 print:grid-cols-2">
        <SeccionInforme id="titulo-competencias" titulo="Competencias desarrolladas" sinCorte>
          <ListaTextos textos={narrativa.competencias_desarrolladas} vacio="Sin competencias registradas." />
        </SeccionInforme>
        <SeccionInforme id="titulo-brechas" titulo="Brechas" sinCorte>
          <ListaTextos textos={narrativa.brechas} vacio="No se identificaron brechas." />
        </SeccionInforme>
      </div>
      <SeccionInforme
        id="titulo-plan"
        titulo="Plan personalizado de fortalecimiento"
        descripcion="Acciones sugeridas, recurso de apoyo, competencia y prioridad."
      >
        <PlanFortalecimiento acciones={narrativa.plan_fortalecimiento} />
      </SeccionInforme>
      <SeccionInforme id="titulo-conclusion" titulo="Conclusión" sinCorte>
        <p className="text-sm leading-relaxed">{narrativa.conclusion || "Sin conclusión registrada."}</p>
      </SeccionInforme>
    </>
  );
}
