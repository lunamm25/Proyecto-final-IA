"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, PlugZap, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TEXTO_PROVEEDOR } from "@/components/docente/modelo-config-ia";
import { mensajeDeError, probarConfigIA } from "@/lib/api";
import type { ConfigIA } from "@/lib/tipos";

type EstadoPrueba =
  | { tipo: "inactivo" }
  | { tipo: "probando" }
  | { tipo: "resultado"; ok: boolean; mensaje: string };

function ResultadoPrueba({ estado }: { estado: EstadoPrueba }) {
  if (estado.tipo === "probando") return <span>Probando conexión…</span>;
  if (estado.tipo !== "resultado") return null;
  const Icono = estado.ok ? CheckCircle2 : XCircle;
  return (
    <span className={`flex items-start gap-2 rounded-lg border p-3 ${estado.ok
      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
      : "border-destructive/30 bg-destructive/5 text-destructive"}`}>
      <Icono className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span>
        <strong>{estado.ok ? "Conexión correcta." : "La conexión falló."}</strong> {estado.mensaje}
      </span>
    </span>
  );
}

/** RF-10 CA2. El contrato no envía cuerpo: el backend prueba la configuración guardada. */
export function PruebaConexion({ guardada, cambiosSinGuardar }: { guardada: ConfigIA; cambiosSinGuardar: boolean }) {
  const [estado, setEstado] = useState<EstadoPrueba>({ tipo: "inactivo" });

  async function probar() {
    setEstado({ tipo: "probando" });
    try {
      const resultado = await probarConfigIA();
      setEstado({ tipo: "resultado", ok: resultado.ok, mensaje: resultado.mensaje });
    } catch (causa) {
      setEstado({ tipo: "resultado", ok: false, mensaje: mensajeDeError(causa) });
    }
  }

  return (
    <section aria-labelledby="titulo-prueba" className="space-y-3">
      <h2 id="titulo-prueba" className="text-lg font-semibold">Probar conexión</h2>
      <p className="text-sm text-muted-foreground">
        Se prueba la configuración guardada: {TEXTO_PROVEEDOR[guardada.proveedor]} con el modelo{" "}
        <span className="font-mono">{guardada.modelo}</span>.
      </p>
      {cambiosSinGuardar && (
        <p className="text-sm text-amber-800">
          Tienes cambios sin guardar. Guárdalos antes si quieres probar la nueva configuración.
        </p>
      )}
      <Button type="button" variant="outline" disabled={estado.tipo === "probando"}
        aria-busy={estado.tipo === "probando"} onClick={() => void probar()}>
        {estado.tipo === "probando" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <PlugZap aria-hidden="true" />}
        {estado.tipo === "probando" ? "Probando…" : "Probar conexión"}
      </Button>
      <div aria-live="polite" role="status" className="text-sm">
        <ResultadoPrueba estado={estado} />
      </div>
    </section>
  );
}
