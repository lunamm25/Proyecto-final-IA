import { EstadoVacio } from "@/components/estados";
import { formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import { NoDisponible } from "@/components/revision/panel-verificacion";
import { nombreVisible } from "@/lib/perfil";
import type { Evaluacion, EventoTraza, JsonValor, Traza } from "@/lib/tipos";

const TEXTO_ACCION: Record<string, string> = {
  lanzar_evaluacion: "Evaluación solicitada",
  evaluacion_completada: "Evaluación completada por la IA",
  revisar: "Paso a revisión",
  ajustar_criterio: "Ajuste de criterio",
  ajuste_criterio: "Ajuste de criterio",
  editar_retroalimentacion: "Edición de retroalimentación",
  restablecer_retroalimentacion: "Texto restablecido al de la IA",
  aprobar: "Aprobación",
  publicar: "Publicación",
};

const SIN_DATO = "No disponible";

/** Muestra un valor de auditoría de forma legible ({nivel_final: "Bueno"} → "nivel_final: Bueno"). */
function describir(valor: JsonValor | null): string {
  if (valor === null) return "—";
  if (typeof valor !== "object") return String(valor);
  if (Array.isArray(valor)) return valor.map(describir).join(", ");
  return Object.entries(valor)
    .map(([clave, v]) => `${clave}: ${describir(v)}`)
    .join(", ");
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="text-sm font-medium break-words">{valor ?? SIN_DATO}</dd>
    </div>
  );
}

function fecha(iso: string | null): string {
  return iso ? formatearFechaHora(iso) : "—";
}

function ItemEvento({ evento }: { evento: EventoTraza }) {
  const hayCambio = evento.antes !== null || evento.despues !== null;
  return (
    <li className="rounded-lg border p-3 text-sm">
      <div className="flex flex-wrap justify-between gap-2">
        <span className="font-semibold">{TEXTO_ACCION[evento.accion] ?? evento.accion}</span>
        <time dateTime={evento.fecha} className="text-xs text-muted-foreground">
          {formatearFechaHora(evento.fecha)}
        </time>
      </div>
      <p className="text-xs text-muted-foreground">
        {evento.usuario ? `Por ${nombreVisible(evento.usuario.nombre, "usuario sin nombre")}` : "Por el sistema"}
      </p>
      {hayCambio && (
        <p className="mt-1 break-words">
          <span className="text-muted-foreground">{describir(evento.antes)}</span>
          <span aria-hidden="true"> → </span>
          <span className="sr-only"> cambió a </span>
          <span className="font-medium">{describir(evento.despues)}</span>
        </p>
      )}
      {evento.motivo && <p className="mt-1">Motivo: {evento.motivo}</p>}
    </li>
  );
}

/** Trazabilidad de la evaluación (RNF-03): modelo, versiones, fechas y eventos de auditoría. */
export function PanelTraza({ traza, evaluacion }: { traza: Traza; evaluacion: Evaluacion }) {
  return (
    <div className="space-y-4">
      <dl className="grid gap-3 rounded-lg border p-3 sm:grid-cols-3">
        <Dato etiqueta="Proveedor" valor={traza.proveedor} />
        <Dato etiqueta="Modelo" valor={traza.modelo} />
        <Dato etiqueta="Temperatura" valor={traza.temperatura === null ? null : traza.temperatura.toLocaleString("es-CO")} />
        <Dato etiqueta="Versión del prompt" valor={traza.prompt_version} />
        <Dato etiqueta="Versión de la rúbrica" valor={traza.rubrica_version === null ? null : `v${traza.rubrica_version}`} />
        <Dato etiqueta="Creada" valor={fecha(evaluacion.creada_en)} />
        <Dato etiqueta="Aprobada" valor={fecha(evaluacion.aprobada_en)} />
        <Dato etiqueta="Publicada" valor={fecha(evaluacion.publicada_en)} />
      </dl>
      <div>
        <h4 className="mb-2 text-sm font-semibold">Eventos</h4>
        {traza.eventos.length === 0 ? (
          <EstadoVacio titulo="Sin eventos registrados" mensaje="Aún no hay ajustes ni cambios de estado." />
        ) : (
          <ol className="space-y-2">
            {traza.eventos.map((evento) => (
              <ItemEvento key={evento.id} evento={evento} />
            ))}
          </ol>
        )}
      </div>
      <NoDisponible
        titulo="Respuesta cruda del modelo no disponible"
        mensaje="El servidor todavía no incluye la respuesta original del modelo en la traza."
      />
    </div>
  );
}
