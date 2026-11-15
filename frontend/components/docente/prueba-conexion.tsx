"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, PlugZap, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { etiquetaProveedor } from "@/components/docente/modelo-config-ia";
import { mensajeDeError, probarConfigIA } from "@/lib/api";
import type { ConfigIA, ResultadoPruebaIA } from "@/lib/tipos";

type EstadoPrueba =
  | { tipo: "inactivo" }
  | { tipo: "probando" }
  | { tipo: "resultado"; resultado: ResultadoPruebaIA }
  | { tipo: "error"; mensaje: string };

function textoLatencia(latencia: number | null): string {
  if (latencia === null) return "";
  return latencia >= 1000 ? ` (${(latencia / 1000).toLocaleString("es-CO", { maximumFractionDigits: 1 })} s)` : ` (${latencia} ms)`;
}

function ResultadoPrueba({ estado, config }: { estado: EstadoPrueba; config: ConfigIA }) {
  if (estado.tipo === "probando") return <span>Probando la conexión… puede tardar hasta 10 segundos.</span>;
  if (estado.tipo === "error") {
    return (
      <span className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-destructive">
        <XCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <span>{estado.mensaje}</span>
      </span>
    );
  }
  if (estado.tipo !== "resultado") return null;
  const { ok, proveedor, modelo, latencia_ms: latencia, mensaje } = estado.resultado;
  const Icono = ok ? CheckCircle2 : XCircle;
  return (
    <span className={`flex items-start gap-2 rounded-lg border p-3 ${ok
      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
      : "border-destructive/30 bg-destructive/5 text-destructive"}`}>
      <Icono className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span>
        <strong>{ok ? "Conexión correcta" : "La conexión falló"}{textoLatencia(latencia)}.</strong> {mensaje}
        <span className="mt-1 block text-xs opacity-80">
          {etiquetaProveedor(config, proveedor)} · <span className="font-mono">{modelo}</span>
        </span>
      </span>
    </span>
  );
}

/**
 * RF-10 CA2. POST /config-ia/probar no lleva cuerpo: prueba la configuración guardada y responde siempre 200;
 * el éxito o fallo lo decide `ok`. Espera hasta ~15 s.
 */
export function PruebaConexion({ guardada, cambiosSinGuardar }: { guardada: ConfigIA; cambiosSinGuardar: boolean }) {
  const [estado, setEstado] = useState<EstadoPrueba>({ tipo: "inactivo" });
  const probando = estado.tipo === "probando";

  async function probar() {
    setEstado({ tipo: "probando" });
    try {
      setEstado({ tipo: "resultado", resultado: await probarConfigIA() });
    } catch (causa) {
      setEstado({ tipo: "error", mensaje: mensajeDeError(causa) });
    }
  }

  return (
    <section aria-labelledby="titulo-prueba" className="space-y-3">
      <h2 id="titulo-prueba" className="text-lg font-semibold">Probar conexión</h2>
      <p className="text-sm text-muted-foreground">
        Se prueba la configuración guardada: {etiquetaProveedor(guardada, guardada.proveedor)} con el modelo{" "}
        <span className="font-mono">{guardada.modelo}</span>.
      </p>
      {cambiosSinGuardar && (
        <p className="text-sm text-amber-800">
          Tienes cambios sin guardar. Guárdalos antes si quieres probar la nueva configuración.
        </p>
      )}
      <Button type="button" variant="outline" disabled={probando} aria-busy={probando} onClick={() => void probar()}>
        {probando ? <Loader2 className="animate-spin" aria-hidden="true" /> : <PlugZap aria-hidden="true" />}
        {probando ? "Probando…" : "Probar conexión"}
      </Button>
      <div aria-live="polite" role="status" className="text-sm">
        <ResultadoPrueba estado={estado} config={guardada} />
      </div>
    </section>
  );
}
