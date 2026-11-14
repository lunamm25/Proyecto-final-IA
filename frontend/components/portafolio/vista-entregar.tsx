"use client";

import Link from "next/link";
import { useCallback } from "react";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { Cargando, EstadoVacio, MensajeError } from "@/components/estados";
import { useSesion } from "@/components/proveedor-sesion";
import { EtiquetaEstado } from "@/components/portafolio/etiqueta-estado";
import { FormularioEntrega } from "@/components/portafolio/formulario-entrega";
import { VistaRubrica } from "@/components/portafolio/vista-rubrica";
import {
  estadoDeLaboratorio,
  formatearFecha,
  ultimaEntregaPorLaboratorio,
} from "@/components/portafolio/estado-entrega";
import { listarCohortes, listarEntregas, obtenerRubricaVigenteONula } from "@/lib/api";
import { idDesdeUrl, type Cohorte, type Entrega, type IdNumerico, type Laboratorio, type RubricaVersion } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

interface DatosEntregar {
  laboratorio: Laboratorio;
  cohorte: Cohorte;
  rubrica: RubricaVersion | null;
  entregaPrevia: Entrega | undefined;
}

function buscarLaboratorio(cohortes: Cohorte[], labId: IdNumerico): { laboratorio: Laboratorio; cohorte: Cohorte } | null {
  for (const cohorte of cohortes) {
    const laboratorio = cohorte.laboratorios.find((l) => l.id === labId);
    if (laboratorio) return { laboratorio, cohorte };
  }
  return null;
}

const CLASE_VOLVER = "inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground";

function EnlaceVolver() {
  return (
    <Link href="/portafolio" className={CLASE_VOLVER}>
      <ArrowLeft className="size-4" aria-hidden="true" />
      Volver a mi portafolio
    </Link>
  );
}

/** Un objetivo por línea; se quita el guion inicial ("- Objetivo" → "Objetivo") y se omiten las líneas vacías. */
export function lineasObjetivos(objetivos: string | null): string[] {
  return (objetivos ?? "")
    .split("\n")
    .map((linea) => linea.replace(/^\s*-\s*/, "").trim())
    .filter((linea) => linea !== "");
}

function ListaObjetivos({ objetivos }: { objetivos: string | null }) {
  const lineas = lineasObjetivos(objetivos);
  if (lineas.length === 0) {
    return <p className="mt-1 text-sm text-muted-foreground">El docente aún no ha escrito los objetivos.</p>;
  }
  return (
    <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
      {lineas.map((linea, indice) => (
        <li key={`${indice}-${linea}`}>{linea}</li>
      ))}
    </ul>
  );
}

function FichaLaboratorio({ laboratorio, cohorte }: { laboratorio: Laboratorio; cohorte: Cohorte }) {
  return (
    <section aria-labelledby="titulo-laboratorio" className="space-y-3">
      <p className="font-mono text-xs text-muted-foreground">
        {laboratorio.codigo} · {cohorte.nombre}
      </p>
      <h1 id="titulo-laboratorio" className="text-3xl font-bold tracking-tight">
        {laboratorio.titulo}
      </h1>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border p-4">
          <h2 className="text-sm font-semibold">Descripción</h2>
          <p className="mt-1 text-sm whitespace-pre-line text-muted-foreground">
            {laboratorio.descripcion || "El docente aún no ha escrito la descripción."}
          </p>
        </div>
        <div className="rounded-xl border p-4">
          <h2 className="text-sm font-semibold">Objetivos</h2>
          <ListaObjetivos objetivos={laboratorio.objetivos} />
        </div>
      </div>
    </section>
  );
}

function AvisoEntregaPrevia({ entrega }: { entrega: Entrega }) {
  return (
    <div role="note" className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-1">
        <p>
          Ya enviaste una entrega para este laboratorio el {formatearFecha(entrega.creada_en)}{" "}
          <EtiquetaEstado estado={estadoDeLaboratorio(entrega)} />
        </p>
        <p>Si envías otra, se registrará como una entrega nueva y tu portafolio mostrará la más reciente.</p>
      </div>
    </div>
  );
}

function SinRubrica() {
  return (
    <EstadoVacio
      titulo="Este laboratorio aún no tiene rúbrica vigente"
      mensaje="No puedes entregar hasta que el docente apruebe la rúbrica del laboratorio. Vuelve más tarde."
    />
  );
}

function LaboratorioNoEncontrado() {
  return (
    <div className="space-y-4">
      <EnlaceVolver />
      <EstadoVacio titulo="Laboratorio no encontrado" mensaje="El laboratorio que buscas no existe o fue eliminado." />
    </div>
  );
}

export function VistaEntregar({ labId }: { labId: string }) {
  const id = idDesdeUrl(labId);
  if (id === null) return <LaboratorioNoEncontrado />;
  return <VistaEntregarValida labId={id} />;
}

function VistaEntregarValida({ labId }: { labId: IdNumerico }) {
  const { perfil } = useSesion();
  const estudianteId = perfil?.id;

  const cargar = useCallback(async (): Promise<DatosEntregar | null> => {
    const [cohortes, entregas] = await Promise.all([listarCohortes(), listarEntregas(estudianteId)]);
    const encontrado = buscarLaboratorio(cohortes, labId);
    if (!encontrado) return null;
    const rubrica = await obtenerRubricaVigenteONula(labId);
    return { ...encontrado, rubrica, entregaPrevia: ultimaEntregaPorLaboratorio(entregas).get(labId) };
  }, [labId, estudianteId]);

  const { estado, recargar } = useCarga(cargar);

  if (estado.tipo === "cargando") return <Cargando texto="Cargando el laboratorio…" />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar el laboratorio" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  if (!estado.datos) return <LaboratorioNoEncontrado />;

  const { laboratorio, cohorte, rubrica, entregaPrevia } = estado.datos;
  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <EnlaceVolver />
        <FichaLaboratorio laboratorio={laboratorio} cohorte={cohorte} />
      </div>
      {rubrica ? (
        <>
          <VistaRubrica rubrica={rubrica} />
          <section aria-labelledby="titulo-formulario" className="space-y-4">
            <h2 id="titulo-formulario" className="text-xl font-semibold">
              Nueva entrega
            </h2>
            {entregaPrevia && <AvisoEntregaPrevia entrega={entregaPrevia} />}
            <FormularioEntrega laboratorioId={laboratorio.id} versionRubrica={rubrica.version} />
          </section>
        </>
      ) : (
        <SinRubrica />
      )}
    </div>
  );
}
