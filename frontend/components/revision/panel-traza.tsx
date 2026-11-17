import { EstadoVacio } from "@/components/estados";
import { formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import { NoDisponible, PanelVerificacion } from "@/components/revision/panel-verificacion";
import { RespuestaCruda, respuestasCrudasDe, sinRespuestasCrudas } from "@/components/revision/respuesta-cruda";
import { nombreVisible } from "@/lib/perfil";
import type { Evaluacion, EventoTraza, JsonValor, Traza } from "@/lib/tipos";

const TEXTO_ACCION: Record<string, string> = {
  lanzar_evaluacion: "Evaluación solicitada",
  evaluacion_completada: "Evaluación completada por la IA",
  evaluacion_ia: "Evaluación completada por la IA",
  evaluacion_ia_error: "Error en la evaluación de la IA",
  evaluacion_ia_descartada: "Resultado de la IA descartado",
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
  // La respuesta cruda se muestra aparte (colapsada); aquí solo el resto del cambio.
  const despues = sinRespuestasCrudas(evento.despues);
  const hayCambio = evento.antes !== null || despues !== null;
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
          <span className="font-medium">{describir(despues)}</span>
        </p>
      )}
      {evento.motivo && <p className="mt-1">Motivo: {evento.motivo}</p>}
    </li>
  );
}

/** Respuestas crudas del evento más reciente que las tenga (la última ejecución de la IA). */
function ultimasRespuestasCrudas(eventos: EventoTraza[]): string[] {
  const conCrudas = eventos.filter((evento) => respuestasCrudasDe(evento).length > 0);
  if (conCrudas.length === 0) return [];
  const ultimo = conCrudas.reduce((a, b) => (Date.parse(b.fecha) >= Date.parse(a.fecha) ? b : a));
  return respuestasCrudasDe(ultimo);
}

/** Trazabilidad de la evaluación (RNF-03): modelo, versiones, fechas, verificación técnica y eventos de auditoría. */
export function PanelTraza({ traza, evaluacion }: { traza: Traza; evaluacion: Evaluacion }) {
  const respuestasCrudas = ultimasRespuestasCrudas(traza.eventos);
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
        <h4 className="mb-2 text-sm font-semibold">Verificación técnica registrada</h4>
        <PanelVerificacion verificacion={traza.verificacion} />
      </div>
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
      <div>
        <h4 className="mb-2 text-sm font-semibold">Respuesta cruda de la IA</h4>
        {respuestasCrudas.length > 0 ? (
          <RespuestaCruda respuestas={respuestasCrudas} />
        ) : (
          <NoDisponible
            titulo="Sin respuesta cruda registrada"
            mensaje="La traza de esta evaluación no incluye la respuesta original del modelo."
          />
        )}
      </div>
    </div>
  );
}
