"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Cargando, MensajeError } from "@/components/estados";
import { EditorRubrica } from "@/components/rubricas/editor-rubrica";
import { listarCohortes, obtenerRubricaVigenteONula } from "@/lib/api";
import type { Cohorte, Laboratorio, RubricaVersion } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

interface DatosRubrica {
  laboratorio: Laboratorio;
  cohorte: Cohorte;
  vigente: RubricaVersion | null;
}

async function cargarDatos(labId: string): Promise<DatosRubrica | null> {
  const [cohortes, vigente] = await Promise.all([listarCohortes(), obtenerRubricaVigenteONula(labId)]);
  for (const cohorte of cohortes) {
    const laboratorio = cohorte.laboratorios.find((l) => l.id === labId);
    if (laboratorio) return { laboratorio, cohorte, vigente };
  }
  return null;
}

const formatoFecha = new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" });

function EnlaceVolver() {
  return (
    <Link href="/docente/laboratorios" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft className="size-4" aria-hidden="true" />
      Volver a laboratorios
    </Link>
  );
}

function Cabecera({ laboratorio, cohorte, vigente }: DatosRubrica) {
  return (
    <header className="space-y-2">
      <EnlaceVolver />
      <p className="font-mono text-xs text-muted-foreground">
        {laboratorio.codigo} · {cohorte.nombre}
      </p>
      <h1 className="text-3xl font-bold tracking-tight">Rúbrica: {laboratorio.titulo}</h1>
      {vigente ? (
        <p className="text-sm text-muted-foreground">
          Versión vigente: <strong className="text-foreground">{vigente.version}</strong> (aprobada el{" "}
          {formatoFecha.format(new Date(vigente.creada_en))}). Al guardar se crea una versión nueva.
        </p>
      ) : (
        <p className="text-sm text-amber-700">
          Este laboratorio aún no tiene rúbrica vigente. Empieza desde cero o sube un archivo para extraerla con IA.
        </p>
      )}
    </header>
  );
}

/** Pantalla /docente/rubricas/[labId]: carga el laboratorio y su versión vigente, y muestra el editor. */
export function VistaEditorRubrica({ labId }: { labId: string }) {
  const { estado, recargar } = useCarga(useCallback(() => cargarDatos(labId), [labId]));
  const [guardada, setGuardada] = useState<RubricaVersion | null>(null);

  if (estado.tipo === "cargando") return <Cargando texto="Cargando la rúbrica…" />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar la rúbrica" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  if (!estado.datos) {
    return (
      <MensajeError titulo="Laboratorio no encontrado" mensaje="El laboratorio que buscas no existe o fue eliminado.">
        <div className="mt-4">
          <EnlaceVolver />
        </div>
      </MensajeError>
    );
  }

  const datos = { ...estado.datos, vigente: guardada ?? estado.datos.vigente };
  return (
    <>
      <Cabecera {...datos} />
      <EditorRubrica laboratorio={datos.laboratorio} vigente={datos.vigente} alGuardar={setGuardada} />
    </>
  );
}
