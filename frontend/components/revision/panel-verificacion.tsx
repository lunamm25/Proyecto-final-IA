import { CheckCircle2, XCircle } from "lucide-react";
import { EstadoVacio } from "@/components/estados";
import type { MetricasCodigo, ResultadoSintaxis, ResultadoTests, VerificacionCodigo } from "@/lib/tipos";

function numero(valor: number): string {
  return valor.toLocaleString("es-CO", { maximumFractionDigits: 2 });
}

function SiNo({ valor }: { valor: boolean }) {
  return valor ? (
    <span className="inline-flex items-center gap-1 text-emerald-800">
      <CheckCircle2 className="size-4" aria-hidden="true" /> Sí
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-red-800">
      <XCircle className="size-4" aria-hidden="true" /> No
    </span>
  );
}

function Tarjeta({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border p-3">
      <h4 className="text-sm font-semibold">{titulo}</h4>
      <div className="mt-2 text-sm">{children}</div>
    </div>
  );
}

function Dato({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted-foreground">{etiqueta}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

function Sintaxis({ archivos }: { archivos: ResultadoSintaxis[] }) {
  if (archivos.length === 0) return <p className="text-muted-foreground">No se analizaron archivos Python.</p>;
  return (
    <ul className="space-y-1">
      {archivos.map((a) => (
        <li key={a.archivo}>
          <span className="font-mono text-xs">{a.archivo}</span>{" "}
          {a.valido ? (
            <span className="text-emerald-800">válido</span>
          ) : (
            <span className="text-red-800">error: {a.error ?? "sin detalle"}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function Tests({ tests }: { tests: ResultadoTests }) {
  if (!tests.ejecutados) {
    return <p className="text-muted-foreground">No se ejecutaron tests{tests.detalle ? `: ${tests.detalle}` : "."}</p>;
  }
  return (
    <>
      <dl className="space-y-1">
        <Dato etiqueta="Aprobados">{tests.aprobados}</Dato>
        <Dato etiqueta="Fallidos">{tests.fallidos}</Dato>
      </dl>
      {tests.detalle && <p className="mt-2 text-xs text-muted-foreground">{tests.detalle}</p>}
    </>
  );
}

function Metricas({ metricas }: { metricas: MetricasCodigo }) {
  return (
    <dl className="space-y-1">
      <Dato etiqueta="Archivos">{numero(metricas.archivos)}</Dato>
      <Dato etiqueta="Líneas">{numero(metricas.lineas)}</Dato>
      <Dato etiqueta="README"><SiNo valor={metricas.tiene_readme} /></Dato>
      <Dato etiqueta="requirements"><SiNo valor={metricas.tiene_requirements} /></Dato>
      <Dato etiqueta="Tests"><SiNo valor={metricas.tiene_tests} /></Dato>
      <Dato etiqueta="Lenguajes">{metricas.lenguajes.join(", ") || "—"}</Dato>
    </dl>
  );
}

/** Resultados objetivos del análisis del código (RF-06). */
export function PanelVerificacion({ verificacion }: { verificacion: VerificacionCodigo | null }) {
  if (!verificacion) {
    return (
      <EstadoVacio
        titulo="Sin verificación técnica"
        mensaje="Esta evaluación no tiene resultados de análisis de código (puede que la entrega no incluyera código)."
      />
    );
  }
  const { ruff, complejidad } = verificacion;
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Tarjeta titulo="Sintaxis"><Sintaxis archivos={verificacion.sintaxis} /></Tarjeta>
      <Tarjeta titulo="Ruff">
        <dl className="space-y-1">
          <Dato etiqueta="Errores">{ruff.errores}</Dato>
          <Dato etiqueta="Advertencias">{ruff.advertencias}</Dato>
        </dl>
        {ruff.mensajes.length > 0 && (
          <ul className="mt-2 space-y-1 font-mono text-xs break-words">
            {ruff.mensajes.map((m) => <li key={m}>{m}</li>)}
          </ul>
        )}
      </Tarjeta>
      <Tarjeta titulo="Complejidad (radon)">
        <dl className="space-y-1">
          <Dato etiqueta="Promedio">{numero(complejidad.promedio)}</Dato>
          <Dato etiqueta="Máxima">{numero(complejidad.maxima)}</Dato>
          <Dato etiqueta="Rango">{complejidad.rango}</Dato>
        </dl>
      </Tarjeta>
      <Tarjeta titulo="Tests (pytest en sandbox)"><Tests tests={verificacion.tests} /></Tarjeta>
      <Tarjeta titulo="Métricas"><Metricas metricas={verificacion.metricas} /></Tarjeta>
      <Tarjeta titulo="Sandbox y limitaciones">
        <p>Sandbox: <span className="font-medium">{verificacion.sandbox || "—"}</span></p>
        {verificacion.limitaciones.length > 0 ? (
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {verificacion.limitaciones.map((l) => <li key={l}>{l}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-muted-foreground">Sin limitaciones reportadas.</p>
        )}
      </Tarjeta>
    </div>
  );
}
