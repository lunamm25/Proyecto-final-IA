"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MAX_MOTIVO_ROL, ROLES, TEXTO_ROL, esRol, motivoBloqueo } from "@/components/admin/reglas-usuarios";
import { cambiarRol, mensajeDeError } from "@/lib/api";
import { nombreVisible } from "@/lib/perfil";
import type { Perfil, Rol, Usuario } from "@/lib/tipos";

interface CambioRolProps {
  usuario: Usuario;
  actual: Perfil;
  /** Prefijo para que los id sean únicos (la fila se pinta en tabla y en tarjeta). */
  idBase: string;
  alActualizar: (usuario: Usuario) => void;
}

type Resultado = { tipo: "exito" | "error"; mensaje: string } | null;

interface ConfirmacionProps {
  id: string;
  pregunta: string;
  enviando: boolean;
  alConfirmar: (motivo: string) => void;
  alCancelar: () => void;
}

/** Confirmación con motivo opcional (queda en la auditoría del backend). */
function Confirmacion({ id, pregunta, enviando, alConfirmar, alCancelar }: ConfirmacionProps) {
  const refMotivo = useRef<HTMLInputElement>(null);
  const [motivo, setMotivo] = useState("");
  useEffect(() => refMotivo.current?.focus(), []);
  return (
    <div role="alertdialog" aria-labelledby={id} className="mt-2 space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3">
      <p id={id} className="text-sm text-amber-900">{pregunta}</p>
      <div className="flex flex-col gap-1">
        <label htmlFor={`${id}-motivo`} className="text-xs font-medium text-amber-900">Motivo (opcional)</label>
        <input ref={refMotivo} id={`${id}-motivo`} value={motivo} maxLength={MAX_MOTIVO_ROL} disabled={enviando}
          aria-describedby={`${id}-motivo-ayuda`} onChange={(e) => setMotivo(e.target.value)}
          className="h-8 rounded-md border bg-background px-2 text-sm" />
        <p id={`${id}-motivo-ayuda`} className="text-xs text-amber-900/80">
          Queda en la auditoría. Máximo {MAX_MOTIVO_ROL} caracteres.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => alConfirmar(motivo)} disabled={enviando} aria-busy={enviando}>
          {enviando && <Loader2 className="animate-spin" aria-hidden="true" />}
          {enviando ? "Cambiando…" : "Sí, cambiar"}
        </Button>
        <Button size="sm" variant="outline" onClick={alCancelar} disabled={enviando}>Cancelar</Button>
      </div>
    </div>
  );
}

function textoPregunta(usuario: Usuario, nuevo: Rol): string {
  const anterior = TEXTO_ROL[usuario.rol].toLowerCase();
  return `¿Cambiar el rol de ${nombreVisible(usuario.nombre, "este usuario")} de ${anterior} a ${TEXTO_ROL[nuevo].toLowerCase()}?`;
}

/**
 * Selector de rol con confirmación y motivo opcional; PATCH /usuarios/{id}/rol y actualiza la fila con la respuesta.
 * Los 404, 422 y 409 se muestran con el `detail` del backend tal cual.
 */
export function CambioRol({ usuario, actual, idBase, alActualizar }: CambioRolProps) {
  const [pendiente, setPendiente] = useState<Rol | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<Resultado>(null);
  const bloqueo = motivoBloqueo(usuario, actual);
  const idSelector = `${idBase}-rol-${usuario.id}`;

  async function confirmar(nuevo: Rol, motivo: string) {
    setEnviando(true);
    try {
      const actualizado = await cambiarRol(usuario.id, nuevo, motivo);
      setPendiente(null);
      setResultado({ tipo: "exito", mensaje: `Rol actualizado a ${TEXTO_ROL[actualizado.rol].toLowerCase()}.` });
      alActualizar(actualizado);
    } catch (causa) {
      setResultado({ tipo: "error", mensaje: mensajeDeError(causa) });
    } finally {
      setEnviando(false);
    }
  }

  function elegir(valor: string) {
    setResultado(null);
    setPendiente(esRol(valor) && valor !== usuario.rol ? valor : null);
  }

  return (
    <div className="min-w-48">
      <label htmlFor={idSelector} className="sr-only">Rol de {nombreVisible(usuario.nombre, "este usuario")}</label>
      <div className="flex items-center gap-2">
        <select id={idSelector} value={pendiente ?? usuario.rol} disabled={bloqueo !== null || enviando}
          aria-describedby={bloqueo ? `${idSelector}-bloqueo` : undefined}
          onChange={(e) => elegir(e.target.value)}
          className="h-9 w-full rounded-lg border bg-background px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60">
          {ROLES.map((rol) => (
            <option key={rol} value={rol}>{TEXTO_ROL[rol]}</option>
          ))}
        </select>
        {enviando && <Loader2 className="size-4 shrink-0 animate-spin" aria-label="Guardando el cambio de rol" />}
      </div>
      {bloqueo && <p id={`${idSelector}-bloqueo`} className="mt-1 text-xs text-muted-foreground">{bloqueo}</p>}
      {pendiente && (
        <Confirmacion id={`${idSelector}-pregunta`} pregunta={textoPregunta(usuario, pendiente)} enviando={enviando}
          alConfirmar={(motivo) => void confirmar(pendiente, motivo)} alCancelar={() => setPendiente(null)} />
      )}
      <div aria-live="polite" className="text-xs">
        {resultado && (
          <p role={resultado.tipo === "error" ? "alert" : undefined}
            className={`mt-1 ${resultado.tipo === "error" ? "text-destructive" : "text-emerald-700"}`}>
            {resultado.mensaje}
          </p>
        )}
      </div>
    </div>
  );
}
