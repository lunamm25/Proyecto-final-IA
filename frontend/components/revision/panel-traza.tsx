import { EstadoVacio } from "@/components/estados";
import { formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import type { Evaluacion, JsonValor, RegistroAuditoria, Traza } from "@/lib/tipos";

const TEXTO_ACCION: Record<string, string> = {
  ajuste_criterio: "Ajuste de criterio",
  aprobar: "Aprobación",
  publicar: "Publicación",
};

/** Muestra un valor de auditoría de forma legible ({nivel_final: "Bueno"} → "nivel_final: Bueno"). */
function describir(valor: JsonValor): string {
  if (valor === null) return "—";
  if (typeof valor !== "object") return String(valor);
  if (Array.isArray(valor)) return valor.map(describir).join(", ");
  return Object.entries(valor)
    .map(([clave, v]) => `${clave}: ${describir(v)}`)
    .join(", ");
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="text-sm font-medium break-words">{valor}</dd>
    </div>
  );
}

function ItemAuditoria({ registro }: { registro: RegistroAuditoria }) {
  return (
    <li className="rounded-lg border p-3 text-sm">
      <div className="flex flex-wrap justify-between gap-2">
        <span className="font-semibold">{TEXTO_ACCION[registro.accion] ?? registro.accion}</span>
        <time dateTime={registro.creado_en} className="text-xs text-muted-foreground">
          {formatearFechaHora(registro.creado_en)}
        </time>
      </div>
      <p className="text-xs text-muted-foreground">Por {registro.usuario_nombre || registro.usuario_id}</p>
      <p className="mt-1 break-words">
        <span className="text-muted-foreground">{describir(registro.antes)}</span>
        <span aria-hidden="true"> → </span>
        <span className="sr-only"> cambió a </span>
        <span className="font-medium">{describir(registro.despues)}</span>
      </p>
      {registro.motivo && <p className="mt-1">Motivo: {registro.motivo}</p>}
    </li>
  );
}

/** Trazabilidad de la evaluación (RNF-03): modelo, versiones, fechas, auditoría y respuesta cruda. */
export function PanelTraza({ traza, evaluacion }: { traza: Traza; evaluacion: Evaluacion }) {
  return (
    <div className="space-y-4">
      <dl className="grid gap-3 rounded-lg border p-3 sm:grid-cols-3">
        <Dato etiqueta="Proveedor" valor={traza.proveedor} />
        <Dato etiqueta="Modelo" valor={traza.modelo} />
        <Dato etiqueta="Temperatura" valor={traza.temperatura.toLocaleString("es-CO")} />
        <Dato etiqueta="Versión del prompt" valor={traza.prompt_version} />
        <Dato etiqueta="Versión de la rúbrica" valor={`v${traza.rubrica_version}`} />
        <Dato etiqueta="Creada" valor={formatearFechaHora(evaluacion.creada_en)} />
        <Dato etiqueta="Aprobada" valor={evaluacion.aprobada_en ? formatearFechaHora(evaluacion.aprobada_en) : "—"} />
        <Dato etiqueta="Publicada" valor={evaluacion.publicada_en ? formatearFechaHora(evaluacion.publicada_en) : "—"} />
      </dl>
      <div>
        <h4 className="mb-2 text-sm font-semibold">Auditoría</h4>
        {traza.auditoria.length === 0 ? (
          <EstadoVacio titulo="Sin cambios registrados" mensaje="Aún no hay ajustes ni cambios de estado." />
        ) : (
          <ol className="space-y-2">
            {traza.auditoria.map((registro) => (
              <ItemAuditoria key={registro.id} registro={registro} />
            ))}
          </ol>
        )}
      </div>
      <details className="rounded-lg border p-3">
        <summary className="cursor-pointer text-sm font-semibold">Respuesta cruda del modelo</summary>
        <pre className="mt-3 max-h-96 overflow-auto rounded bg-muted p-3 text-xs">
          {JSON.stringify(traza.respuesta_cruda, null, 2)}
        </pre>
      </details>
    </div>
  );
}
