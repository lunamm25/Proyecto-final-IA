"use client";

import Link from "next/link";
import { useCallback } from "react";
import { Inbox } from "lucide-react";
import { MensajeError } from "@/components/estados";
import { formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import { BotonDescargarPdf } from "@/components/informe/boton-descargar-pdf";
import { EsqueletoInforme } from "@/components/informe/esqueleto-informe";
import { GraficaDominio } from "@/components/informe/grafica-dominio";
import { GraficaEvolucion } from "@/components/informe/grafica-evolucion";
import { NarrativaInforme } from "@/components/informe/narrativa-informe";
import { TablaNotas } from "@/components/informe/tabla-notas";
import { TarjetasKpi } from "@/components/informe/tarjetas-kpi";
import { useModoImpresion } from "@/components/informe/use-impresion";
import { useSesion } from "@/components/proveedor-sesion";
import { ErrorApi, obtenerInforme } from "@/lib/api";
import type { Informe } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

const CLASE_ENLACE = "mt-4 inline-block text-sm font-medium underline underline-offset-4";

type ResultadoInforme =
  | { tipo: "ok"; informe: Informe }
  | { tipo: "denegado"; mensaje: string }
  | { tipo: "no_encontrado"; mensaje: string };

/** Pide el informe y separa 403/404 (mensajes propios) del resto de errores (con Reintentar). */
async function cargarInforme(estudianteId: string): Promise<ResultadoInforme> {
  try {
    return { tipo: "ok", informe: await obtenerInforme(estudianteId) };
  } catch (causa) {
    if (causa instanceof ErrorApi && causa.status === 403) return { tipo: "denegado", mensaje: causa.message };
    if (causa instanceof ErrorApi && causa.status === 404) return { tipo: "no_encontrado", mensaje: causa.message };
    throw causa;
  }
}

function SinPermiso({ mensaje }: { mensaje: string }) {
  return (
    <MensajeError titulo="No tienes permiso para ver este informe" mensaje={`Error 403: ${mensaje}`}>
      <Link href="/informe" className={CLASE_ENLACE}>
        Ir a mi informe
      </Link>
    </MensajeError>
  );
}

function NoEncontrado({ mensaje }: { mensaje: string }) {
  return (
    <MensajeError titulo="Informe no encontrado" mensaje={`Error 404: ${mensaje}`}>
      <Link href="/" className={CLASE_ENLACE}>
        Volver al inicio
      </Link>
    </MensajeError>
  );
}

function SinEvaluaciones({ informe, esEstudiante }: { informe: Informe; esEstudiante: boolean }) {
  return (
    <div className="mx-auto my-12 max-w-lg rounded-xl border border-dashed p-6 text-center">
      <Inbox className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
      <h2 className="mt-3 text-lg font-semibold">
        {esEstudiante ? "Aún no tienes evaluaciones publicadas" : `${informe.estudiante_nombre} aún no tiene evaluaciones publicadas`}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        El informe se construye solo con evaluaciones publicadas y validadas por el docente.
        {esEstudiante && " Sube tus laboratorios y, cuando el docente publique su revisión, aquí verás tu informe."}
      </p>
      <Link href={esEstudiante ? "/portafolio" : "/docente/revision"} className={CLASE_ENLACE}>
        {esEstudiante ? "Ir a mi portafolio" : "Ir a la bandeja de revisión"}
      </Link>
    </div>
  );
}

function Cabecera({ informe }: { informe: Informe }) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">Informe integral del aprendizaje</p>
        <h1 className="text-2xl font-bold">{informe.estudiante_nombre}</h1>
        <p className="mt-1 text-sm text-muted-foreground">Generado el {formatearFechaHora(informe.generado_en)}</p>
        <p role="note" className="mt-2 text-sm">
          Basado solo en evaluaciones publicadas y validadas por el docente.
        </p>
      </div>
      <BotonDescargarPdf nombreEstudiante={informe.estudiante_nombre} />
    </header>
  );
}

function InformeCompleto({ informe }: { informe: Informe }) {
  const imprimiendo = useModoImpresion();
  return (
    <article className="informe-imprimible space-y-6">
      <Cabecera informe={informe} />
      <TarjetasKpi informe={informe} />
      <GraficaEvolucion notas={informe.notas_laboratorio} evolucion={informe.evolucion} imprimiendo={imprimiendo} />
      <GraficaDominio dominios={informe.dominio_competencias} imprimiendo={imprimiendo} />
      <TablaNotas notas={informe.notas_laboratorio} />
      <NarrativaInforme narrativa={informe.narrativa} />
    </article>
  );
}

function ContenidoInforme({ estudianteId, esEstudiante }: { estudianteId: string; esEstudiante: boolean }) {
  const cargar = useCallback(() => cargarInforme(estudianteId), [estudianteId]);
  const { estado, recargar } = useCarga(cargar);

  if (estado.tipo === "cargando") return <EsqueletoInforme />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar el informe" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  const resultado = estado.datos;
  if (resultado.tipo === "denegado") return <SinPermiso mensaje={resultado.mensaje} />;
  if (resultado.tipo === "no_encontrado") return <NoEncontrado mensaje={resultado.mensaje} />;
  if (resultado.informe.notas_laboratorio.length === 0) {
    return <SinEvaluaciones informe={resultado.informe} esEstudiante={esEstudiante} />;
  }
  return <InformeCompleto informe={resultado.informe} />;
}

/**
 * Informe de un estudiante (RF-08). El estudiante solo puede ver el suyo; docente y admin, cualquiera.
 * Debe usarse dentro de GuardaRol (garantiza que hay perfil). El backend aplica el permiso real.
 */
export function VistaInforme({ estudianteId }: { estudianteId: string }) {
  const { perfil } = useSesion();
  if (!perfil) return null;
  const esEstudiante = perfil.rol === "estudiante";
  if (esEstudiante && perfil.id !== estudianteId) return <SinPermiso mensaje="Solo puedes ver tu propio informe." />;
  return <ContenidoInforme estudianteId={estudianteId} esEstudiante={esEstudiante} />;
}

/** Informe del estudiante que tiene la sesión abierta (/informe). */
export function VistaInformePropio() {
  const { perfil } = useSesion();
  if (!perfil) return null;
  return <ContenidoInforme estudianteId={perfil.id} esEstudiante />;
}
