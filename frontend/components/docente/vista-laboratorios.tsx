"use client";

import Link from "next/link";
import { useState } from "react";
import { ClipboardList, Pencil, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EstadoVacio, MensajeError } from "@/components/estados";
import { Aviso, type DatosAviso } from "@/components/docente/aviso";
import { DialogoLaboratorio } from "@/components/docente/dialogo-laboratorio";
import { listarCohortes, obtenerRubricaVigenteONula } from "@/lib/api";
import type { Cohorte, Laboratorio, RubricaVersion } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

/** "error" = no se pudo consultar la rúbrica de ese laboratorio (no bloquea la lista). */
type EstadoRubrica = RubricaVersion | null | "error";

interface DatosLaboratorios {
  cohortes: Cohorte[];
  rubricas: Map<string, EstadoRubrica>;
}

/** null = diálogo cerrado; laboratorio null = crear uno nuevo. */
type Edicion = { laboratorio: Laboratorio | null } | null;

async function rubricaDe(labId: string): Promise<[string, EstadoRubrica]> {
  try {
    return [labId, await obtenerRubricaVigenteONula(labId)];
  } catch {
    return [labId, "error"];
  }
}

async function cargarLaboratorios(): Promise<DatosLaboratorios> {
  const cohortes = [...(await listarCohortes())].sort((a, b) => a.numero - b.numero);
  const ids = cohortes.flatMap((c) => c.laboratorios.map((l) => l.id));
  return { cohortes, rubricas: new Map(await Promise.all(ids.map(rubricaDe))) };
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

function EtiquetaRubrica({ estado }: { estado: EstadoRubrica | undefined }) {
  if (estado === "error") return <span className="text-xs text-destructive">No se pudo consultar la rúbrica</span>;
  if (!estado) {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">Sin rúbrica vigente</span>
    );
  }
  return (
    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900">
      Rúbrica vigente: versión {estado.version}
    </span>
  );
}

interface FilaLaboratorioProps {
  laboratorio: Laboratorio;
  rubrica: EstadoRubrica | undefined;
  alEditar: () => void;
}

function FilaLaboratorio({ laboratorio, rubrica, alEditar }: FilaLaboratorioProps) {
  return (
    <li className="flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">{laboratorio.codigo}</span>
          <EtiquetaRubrica estado={rubrica} />
        </div>
        <h3 className="font-semibold">{laboratorio.titulo}</h3>
        <p className="line-clamp-2 text-sm text-muted-foreground">{laboratorio.descripcion}</p>
      </div>
      <div className="flex shrink-0 gap-2">
        <Button variant="outline" size="sm" onClick={alEditar} aria-label={`Editar ${laboratorio.codigo}`}>
          <Pencil aria-hidden="true" />
          Editar
        </Button>
        <Button variant="secondary" size="sm" asChild>
          <Link href={`/docente/rubricas/${encodeURIComponent(laboratorio.id)}`} aria-label={`Rúbrica de ${laboratorio.codigo}`}>
            <ClipboardList aria-hidden="true" />
            Rúbrica
          </Link>
        </Button>
      </div>
    </li>
  );
}

interface SeccionCohorteProps {
  cohorte: Cohorte;
  rubricas: Map<string, EstadoRubrica>;
  alEditar: (laboratorio: Laboratorio) => void;
}

function SeccionCohorte({ cohorte, rubricas, alEditar }: SeccionCohorteProps) {
  return (
    <section aria-labelledby={`cohorte-${cohorte.id}`} className="space-y-3">
      <h2 id={`cohorte-${cohorte.id}`} className="text-xl font-semibold">
        {cohorte.nombre}
      </h2>
      {cohorte.laboratorios.length === 0 ? (
        <p className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
          Esta cohorte aún no tiene laboratorios.
        </p>
      ) : (
        <ul className="space-y-3">
          {cohorte.laboratorios.map((lab) => (
            <FilaLaboratorio key={lab.id} laboratorio={lab} rubrica={rubricas.get(lab.id)} alEditar={() => alEditar(lab)} />
          ))}
        </ul>
      )}
    </section>
  );
}

/** Lista de laboratorios por cohorte con crear/editar (RF-02 CA1) y estado de la rúbrica vigente (CA2). */
export function VistaLaboratorios() {
  const { estado, recargar, refrescar } = useCarga(cargarLaboratorios);
  const [edicion, setEdicion] = useState<Edicion>(null);
  const [aviso, setAviso] = useState<DatosAviso | null>(null);

  if (estado.tipo === "cargando") return <EsqueletoLaboratorios />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudieron cargar los laboratorios" mensaje={estado.mensaje} alReintentar={recargar} />;
  }

  const { cohortes, rubricas } = estado.datos;

  function alGuardar(laboratorio: Laboratorio) {
    const accion = edicion?.laboratorio ? "actualizó" : "creó";
    setEdicion(null);
    setAviso({ tipo: "exito", mensaje: `Se ${accion} el laboratorio ${laboratorio.codigo}.` });
    refrescar();
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
        <EstadoVacio titulo="No hay cohortes registradas" mensaje="Cuando el backend cargue las cohortes 1 y 2, aparecerán aquí." />
      ) : (
        cohortes.map((cohorte) => (
          <SeccionCohorte key={cohorte.id} cohorte={cohorte} rubricas={rubricas}
            alEditar={(laboratorio) => setEdicion({ laboratorio })} />
        ))
      )}
      {edicion && (
        <DialogoLaboratorio key={edicion.laboratorio?.id ?? "nuevo"} laboratorio={edicion.laboratorio}
          cohortes={cohortes} alCerrar={() => setEdicion(null)} alGuardar={alGuardar} />
      )}
    </div>
  );
}
