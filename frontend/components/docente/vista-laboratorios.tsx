"use client";

import Link from "next/link";
import { useState } from "react";
import { ClipboardList, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EstadoVacio, MensajeError } from "@/components/estados";
import { Aviso, type DatosAviso } from "@/components/docente/aviso";
import { DialogoLaboratorio } from "@/components/docente/dialogo-laboratorio";
import { eliminarLaboratorio, listarCohortes, mensajeDeError } from "@/lib/api";
import type { Cohorte, IdNumerico, Laboratorio, LaboratorioEnCohorte } from "@/lib/tipos";
import { textoCorte } from "@/lib/corte";
import { useCarga } from "@/lib/use-carga";

/** null = diálogo cerrado; laboratorio null = crear uno nuevo. */
type Edicion = { laboratorio: Laboratorio | null } | null;

/** GET /cohortes ya trae `version_rubrica_vigente` de cada laboratorio: una sola petición. */
async function cargarLaboratorios(): Promise<Cohorte[]> {
  return [...(await listarCohortes())].sort((a, b) => a.numero - b.numero);
}

function EsqueletoLaboratorios() {
  return (
    <div role="status" aria-label="Cargando laboratorios" className="mt-8 space-y-3">
      {[0, 1, 2].map((fila) => (
        <div key={fila} className="h-20 animate-pulse rounded-xl bg-muted" />
      ))}
      <span className="sr-only">Cargando laboratorios…</span>
    </div>
  );
}

function EtiquetaRubrica({ version }: { version: number | null }) {
  if (version === null) {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">Sin rúbrica vigente</span>
    );
  }
  return (
    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900">
      Rúbrica vigente: versión {version}
    </span>
  );
}

function mensajeConfirmarEliminar(laboratorio: Laboratorio): string {
  return (
    `¿Eliminar el laboratorio ${laboratorio.codigo} — ${laboratorio.titulo}?\n\n` +
    "También se borran su rúbrica y todas sus versiones. Esta acción no se puede deshacer. " +
    "Si el laboratorio ya tiene entregas, el servidor no permitirá borrarlo."
  );
}

interface FilaLaboratorioProps {
  laboratorio: LaboratorioEnCohorte;
  eliminando: boolean;
  ocupado: boolean;
  alEditar: () => void;
  alEliminar: () => void;
}

function FilaLaboratorio({ laboratorio, eliminando, ocupado, alEditar, alEliminar }: FilaLaboratorioProps) {
  return (
    <li className="flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">{laboratorio.codigo}</span>
          <EtiquetaRubrica version={laboratorio.version_rubrica_vigente} />
        </div>
        <h3 className="font-semibold">{laboratorio.titulo}</h3>
        {laboratorio.descripcion && (
          <p className="line-clamp-2 text-sm text-muted-foreground">{laboratorio.descripcion}</p>
        )}
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={alEditar} disabled={ocupado} aria-label={`Editar ${laboratorio.codigo}`}>
          <Pencil aria-hidden="true" />
          Editar
        </Button>
        <Button variant="secondary" size="sm" asChild>
          <Link href={`/docente/rubricas/${laboratorio.id}`} aria-label={`Rúbrica de ${laboratorio.codigo}`}>
            <ClipboardList aria-hidden="true" />
            Rúbrica
          </Link>
        </Button>
        <Button variant="destructive" size="sm" onClick={alEliminar} disabled={ocupado} aria-busy={eliminando}
          aria-label={`Eliminar ${laboratorio.codigo}`}>
          {eliminando ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Trash2 aria-hidden="true" />}
          {eliminando ? "Eliminando…" : "Eliminar"}
        </Button>
      </div>
    </li>
  );
}

interface SeccionCohorteProps {
  cohorte: Cohorte;
  eliminandoId: IdNumerico | null;
  alEditar: (laboratorio: Laboratorio) => void;
  alEliminar: (laboratorio: Laboratorio) => void;
}

function SeccionCohorte({ cohorte, eliminandoId, alEditar, alEliminar }: SeccionCohorteProps) {
  return (
    <section aria-labelledby={`cohorte-${cohorte.id}`} className="space-y-3">
      <h2 id={`cohorte-${cohorte.id}`} className="text-xl font-semibold">
        {textoCorte(cohorte.nombre)}
      </h2>
      {cohorte.laboratorios.length === 0 ? (
        <p className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
          Esta cohorte aún no tiene laboratorios.
        </p>
      ) : (
        <ul className="space-y-3">
          {cohorte.laboratorios.map((lab) => (
            <FilaLaboratorio key={lab.id} laboratorio={lab} eliminando={eliminandoId === lab.id}
              ocupado={eliminandoId !== null} alEditar={() => alEditar(lab)} alEliminar={() => alEliminar(lab)} />
          ))}
        </ul>
      )}
    </section>
  );
}

/** Lista de laboratorios por corte (cohorte en el backend) con crear/editar/eliminar (RF-02 CA1) y estado de la rúbrica vigente (CA2). */
export function VistaLaboratorios() {
  const { estado, recargar, refrescar } = useCarga(cargarLaboratorios);
  const [edicion, setEdicion] = useState<Edicion>(null);
  const [aviso, setAviso] = useState<DatosAviso | null>(null);
  const [eliminandoId, setEliminandoId] = useState<IdNumerico | null>(null);

  if (estado.tipo === "cargando") return <EsqueletoLaboratorios />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudieron cargar los laboratorios" mensaje={estado.mensaje} alReintentar={recargar} />;
  }

  const cohortes = estado.datos;

  function alGuardar(laboratorio: Laboratorio) {
    const accion = edicion?.laboratorio ? "actualizó" : "creó";
    setEdicion(null);
    setAviso({ tipo: "exito", mensaje: `Se ${accion} el laboratorio ${laboratorio.codigo}.` });
    refrescar();
  }

  async function alEliminar(laboratorio: Laboratorio) {
    if (!window.confirm(mensajeConfirmarEliminar(laboratorio))) return;
    setEliminandoId(laboratorio.id);
    setAviso(null);
    try {
      await eliminarLaboratorio(laboratorio.id);
      setAviso({ tipo: "exito", mensaje: `Se eliminó el laboratorio ${laboratorio.codigo}.` });
      refrescar();
    } catch (causa) {
      // 409 (tiene entregas) y 404 traen `detail` en español: se muestra tal cual.
      setAviso({ tipo: "error", mensaje: mensajeDeError(causa) });
    } finally {
      setEliminandoId(null);
    }
  }

  return (
    <div className="mt-6 space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {aviso ? <Aviso {...aviso} className="flex-1" /> : <span />}
        <Button onClick={() => setEdicion({ laboratorio: null })} disabled={cohortes.length === 0}>
          <Plus aria-hidden="true" />
          Nuevo laboratorio
        </Button>
      </div>
      {cohortes.length === 0 ? (
        <EstadoVacio titulo="No hay cortes registrados" mensaje="Cuando el backend cargue los cortes 1 y 2, aparecerán aquí." />
      ) : (
        cohortes.map((cohorte) => (
          <SeccionCohorte key={cohorte.id} cohorte={cohorte} eliminandoId={eliminandoId}
            alEditar={(laboratorio) => setEdicion({ laboratorio })}
            alEliminar={(laboratorio) => void alEliminar(laboratorio)} />
        ))
      )}
      {edicion && (
        <DialogoLaboratorio key={edicion.laboratorio?.id ?? "nuevo"} laboratorio={edicion.laboratorio}
          cohortes={cohortes} alCerrar={() => setEdicion(null)} alGuardar={alGuardar} />
      )}
    </div>
  );
}
