import { PlanFortalecimiento } from "@/components/informe/plan-fortalecimiento";
import { SeccionInforme } from "@/components/informe/seccion-informe";
import type { EstadoNarrativa, Narrativa } from "@/lib/tipos";

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

const TEXTO_ESTADO: Record<Exclude<EstadoNarrativa, "generada">, string> = {
  sin_datos: "Todavía no hay evaluaciones publicadas suficientes para redactar el análisis.",
  no_disponible: "El análisis narrativo no está disponible en este momento (el servicio de IA no respondió o no está configurado).",
  error: "No se pudo generar el análisis narrativo. Los números del informe siguen siendo válidos.",
};

/** Análisis del aprendizaje (NarrativaRespuesta). Si no está "generada", muestra el estado y el mensaje del backend. */
export function NarrativaInforme({ narrativa }: { narrativa: Narrativa }) {
  if (narrativa.estado !== "generada") {
    return (
      <SeccionInforme id="titulo-narrativa" titulo="Análisis del aprendizaje" sinCorte>
        <p role={narrativa.estado === "error" ? "alert" : undefined} className="text-sm text-muted-foreground">
          {narrativa.mensaje || TEXTO_ESTADO[narrativa.estado]}
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
