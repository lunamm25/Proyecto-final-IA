"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ROLES, TEXTO_ROL, esRol, motivoBloqueo, puedeAsignar } from "@/components/admin/reglas-usuarios";
import { cambiarRol, mensajeDeError } from "@/lib/api";
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
  alConfirmar: () => void;
  alCancelar: () => void;
}

function Confirmacion({ id, pregunta, enviando, alConfirmar, alCancelar }: ConfirmacionProps) {
  const refConfirmar = useRef<HTMLButtonElement>(null);
  useEffect(() => refConfirmar.current?.focus(), []);
  return (
    <div role="alertdialog" aria-labelledby={id} className="mt-2 rounded-lg border border-amber-300 bg-amber-50 p-3">
      <p id={id} className="text-sm text-amber-900">{pregunta}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button ref={refConfirmar} size="sm" onClick={alConfirmar} disabled={enviando} aria-busy={enviando}>
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
  return `¿Cambiar el rol de ${usuario.nombre} de ${anterior} a ${TEXTO_ROL[nuevo].toLowerCase()}?`;
}

/** Selector de rol con confirmación; PATCH /usuarios/{id}/rol y actualiza la fila con la respuesta del backend. */
export function CambioRol({ usuario, actual, idBase, alActualizar }: CambioRolProps) {
  const [pendiente, setPendiente] = useState<Rol | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<Resultado>(null);
  const bloqueo = motivoBloqueo(usuario, actual);
  const idSelector = `${idBase}-rol-${usuario.id}`;

  async function confirmar(nuevo: Rol) {
    setEnviando(true);
    try {
      const actualizado = await cambiarRol(usuario.id, nuevo);
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
      <label htmlFor={idSelector} className="sr-only">Rol de {usuario.nombre}</label>
      <div className="flex items-center gap-2">
        <select id={idSelector} value={pendiente ?? usuario.rol} disabled={bloqueo !== null || enviando}
          aria-describedby={bloqueo ? `${idSelector}-bloqueo` : undefined}
          onChange={(e) => elegir(e.target.value)}
          className="h-9 w-full rounded-lg border bg-background px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60">
          {ROLES.map((rol) => (
            <option key={rol} value={rol} disabled={rol !== usuario.rol && !puedeAsignar(rol, actual)}>
              {TEXTO_ROL[rol]}{rol !== usuario.rol && !puedeAsignar(rol, actual) ? " (solo un administrador)" : ""}
            </option>
          ))}
        </select>
        {enviando && <Loader2 className="size-4 shrink-0 animate-spin" aria-label="Guardando el cambio de rol" />}
      </div>
      {bloqueo && <p id={`${idSelector}-bloqueo`} className="mt-1 text-xs text-muted-foreground">{bloqueo}</p>}
      {pendiente && (
        <Confirmacion id={`${idSelector}-pregunta`} pregunta={textoPregunta(usuario, pendiente)} enviando={enviando}
          alConfirmar={() => void confirmar(pendiente)} alCancelar={() => setPendiente(null)} />
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
