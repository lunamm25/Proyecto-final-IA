"use client";

import Link from "next/link";
import { useCallback } from "react";
import { Inbox } from "lucide-react";
import { MensajeError } from "@/components/estados";
import { formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import { BotonDescargarPdf } from "@/components/informe/boton-descargar-pdf";
import { EsqueletoInforme, MENSAJE_GENERANDO_INFORME } from "@/components/informe/esqueleto-informe";
import { GraficaDominio, type DatoDominio } from "@/components/informe/grafica-dominio";
import { GraficaEvolucion } from "@/components/informe/grafica-evolucion";
import { NarrativaInforme } from "@/components/informe/narrativa-informe";
import { TablaNotas } from "@/components/informe/tabla-notas";
import { TarjetasKpi } from "@/components/informe/tarjetas-kpi";
import { useModoImpresion } from "@/components/informe/use-impresion";
import { useSesion } from "@/components/proveedor-sesion";
import { ElegirEstudiante, ListaAvisos, SelectorEstudiante } from "@/components/selector-estudiante";
import { ErrorApi, obtenerInforme } from "@/lib/api";
import { nombreVisible } from "@/lib/perfil";
import type { CompetenciaInforme, Informe, TematicaInforme } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

const CLASE_ENLACE = "mt-4 inline-block text-sm font-medium underline underline-offset-4";

/** Rangos que usa el backend para nivel_dominio (el frontend no lo calcula, solo lo explica). */
const DESCRIPCION_NIVELES =
  "Promedio de 0 a 5 y nivel de dominio asignado por el sistema: bajo (menos de 3,0), medio (3,0 a 3,9) y alto (4,0 o más).";

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

function nombreDe(informe: Informe): string {
  return nombreVisible(informe.estudiante.nombre, "Estudiante");
}

function competenciasADatos(competencias: CompetenciaInforme[]): DatoDominio[] {
  return competencias.map((c) => ({ nombre: c.competencia, promedio: c.promedio, nivel_dominio: c.nivel_dominio, criterios_evaluados: c.criterios_evaluados }));
}

function tematicasADatos(tematicas: TematicaInforme[]): DatoDominio[] {
  return tematicas.map((t) => ({ nombre: t.tematica, promedio: t.promedio, nivel_dominio: t.nivel_dominio, criterios_evaluados: t.criterios_evaluados }));
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
    <div className="mx-auto my-12 max-w-lg space-y-4 rounded-xl border border-dashed p-6 text-center">
      <Inbox className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
      <h2 className="text-lg font-semibold">
        {esEstudiante ? "Aún no tienes evaluaciones publicadas" : `${nombreDe(informe)} aún no tiene evaluaciones publicadas`}
      </h2>
      <p className="text-sm text-muted-foreground">
        El informe se construye solo con evaluaciones publicadas y validadas por el docente.
        {esEstudiante && " Sube tus laboratorios y, cuando el docente publique su revisión, aquí verás tu informe."}
      </p>
      <div className="text-left">
        <ListaAvisos avisos={informe.avisos} />
      </div>
      <Link href={esEstudiante ? "/portafolio" : "/docente/revision"} className={CLASE_ENLACE}>
        {esEstudiante ? "Ir a mi portafolio" : "Ir a la bandeja de revisión"}
      </Link>
    </div>
  );
}

function Cabecera({ informe }: { informe: Informe }) {
  const generada = informe.narrativa.generada_en;
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">Informe integral del aprendizaje</p>
        <h1 className="text-2xl font-bold">{nombreDe(informe)}</h1>
        {generada && <p className="mt-1 text-sm text-muted-foreground">Análisis generado el {formatearFechaHora(generada)}</p>}
        <p role="note" className="mt-2 text-sm">
          Basado solo en evaluaciones publicadas y validadas por el docente.
        </p>
      </div>
      <BotonDescargarPdf nombreEstudiante={nombreDe(informe)} />
    </header>
  );
}

function InformeCompleto({ informe }: { informe: Informe }) {
  const imprimiendo = useModoImpresion();
  return (
    <article className="informe-imprimible space-y-6">
      <Cabecera informe={informe} />
      <ListaAvisos avisos={informe.avisos} />
      <TarjetasKpi informe={informe} />
      <GraficaEvolucion notas={informe.laboratorios} evolucion={informe.evolucion} imprimiendo={imprimiendo} />
      <GraficaDominio id="titulo-dominio" titulo="Dominio por competencia" columna="Competencia"
        descripcion={DESCRIPCION_NIVELES}
        datos={competenciasADatos(informe.competencias)} imprimiendo={imprimiendo} />
      {informe.tematicas.length > 0 && (
        <GraficaDominio id="titulo-tematicas" titulo="Dominio por temática de IA" columna="Temática"
          descripcion={DESCRIPCION_NIVELES}
          datos={tematicasADatos(informe.tematicas)} imprimiendo={imprimiendo} />
      )}
      <TablaNotas laboratorios={informe.laboratorios} />
      <NarrativaInforme narrativa={informe.narrativa} />
    </article>
  );
}

function ContenidoInforme({ estudianteId, esEstudiante }: { estudianteId: string; esEstudiante: boolean }) {
  const cargar = useCallback(() => cargarInforme(estudianteId), [estudianteId]);
  const { estado, recargar } = useCarga(cargar);

  if (estado.tipo === "cargando") return <EsqueletoInforme mensaje={MENSAJE_GENERANDO_INFORME} />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar el informe" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  const resultado = estado.datos;
  if (resultado.tipo === "denegado") return <SinPermiso mensaje={resultado.mensaje} />;
  if (resultado.tipo === "no_encontrado") return <NoEncontrado mensaje={resultado.mensaje} />;
  if (resultado.informe.narrativa.estado === "sin_datos" || resultado.informe.laboratorios_evaluados === 0) {
    return <SinEvaluaciones informe={resultado.informe} esEstudiante={esEstudiante} />;
  }
  return <InformeCompleto informe={resultado.informe} />;
}

/**
 * Informe de un estudiante (RF-08). El estudiante solo puede ver el suyo; docente y admin, cualquiera
 * (con un selector para cambiar de estudiante). Debe usarse dentro de GuardaRol. El backend aplica el permiso real.
 */
export function VistaInforme({ estudianteId }: { estudianteId: string }) {
  const { perfil } = useSesion();
  if (!perfil) return null;
  const esEstudiante = perfil.rol === "estudiante";
  if (esEstudiante && perfil.id !== estudianteId) return <SinPermiso mensaje="Solo puedes ver tu propio informe." />;
  if (esEstudiante) return <ContenidoInforme estudianteId={estudianteId} esEstudiante />;
  return (
    <div className="space-y-6">
      <SelectorEstudiante destino="informe" actual={estudianteId} />
      <ContenidoInforme estudianteId={estudianteId} esEstudiante={false} />
    </div>
  );
}

/** /informe: el estudiante ve el suyo; docente y admin eligen un estudiante. */
export function VistaInformePropio() {
  const { perfil } = useSesion();
  if (!perfil) return null;
  if (perfil.rol !== "estudiante") return <ElegirEstudiante destino="informe" />;
  return <ContenidoInforme estudianteId={perfil.id} esEstudiante />;
}
