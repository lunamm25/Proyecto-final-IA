"use client";

import Link from "next/link";
import { useCallback } from "react";
import { Inbox } from "lucide-react";
import { MensajeError } from "@/components/estados";
import { EsqueletoMapa, MENSAJE_GENERANDO_MAPA } from "@/components/mapa/esqueleto-mapa";
import { ExploradorMapa } from "@/components/mapa/explorador-mapa";
import { useSesion } from "@/components/proveedor-sesion";
import {
  ElegirEstudiante,
  ListaAvisos,
  SelectorEstudiante,
  nombreEnLista,
  useListaEstudiantes,
} from "@/components/selector-estudiante";
import { ErrorApi, obtenerMapa } from "@/lib/api";
import type { Mapa } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

const CLASE_ENLACE = "mt-4 inline-block text-sm font-medium underline underline-offset-4";

type ResultadoMapa =
  | { tipo: "ok"; mapa: Mapa }
  | { tipo: "denegado"; mensaje: string }
  | { tipo: "no_encontrado"; mensaje: string };

/** Pide el mapa y separa 403/404 (mensajes propios) del resto de errores, incluido el tiempo agotado (con Reintentar). */
async function cargarMapa(estudianteId: string): Promise<ResultadoMapa> {
  try {
    return { tipo: "ok", mapa: await obtenerMapa(estudianteId) };
  } catch (causa) {
    if (causa instanceof ErrorApi && causa.status === 403) return { tipo: "denegado", mensaje: causa.message };
    if (causa instanceof ErrorApi && causa.status === 404) return { tipo: "no_encontrado", mensaje: causa.message };
    throw causa;
  }
}

function SinPermiso({ mensaje }: { mensaje: string }) {
  return (
    <MensajeError titulo="No tienes permiso para ver este mapa" mensaje={`Error 403: ${mensaje}`}>
      <Link href="/mapa" className={CLASE_ENLACE}>
        Ir a mi mapa mental
      </Link>
    </MensajeError>
  );
}

function NoEncontrado({ mensaje }: { mensaje: string }) {
  return (
    <MensajeError titulo="Mapa no encontrado" mensaje={`Error 404: ${mensaje}`}>
      <Link href="/" className={CLASE_ENLACE}>
        Volver al inicio
      </Link>
    </MensajeError>
  );
}

interface PropsSinEvaluaciones {
  nombre: string | null;
  esEstudiante: boolean;
  avisos: string[];
}

function SinEvaluaciones({ nombre, esEstudiante, avisos }: PropsSinEvaluaciones) {
  return (
    <div className="mx-auto my-12 max-w-lg rounded-xl border border-dashed p-6 text-center">
      <Inbox className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
      <h2 className="mt-3 text-lg font-semibold">
        {esEstudiante ? "Aún no tienes evaluaciones publicadas" : `${nombre ?? "Este estudiante"} aún no tiene evaluaciones publicadas`}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        El mapa mental se construye solo con evaluaciones publicadas y validadas por el docente.
        {esEstudiante && " Sube tus laboratorios y, cuando el docente publique su revisión, aquí verás tus competencias."}
      </p>
      <div className="mt-4 text-left">
        <ListaAvisos avisos={avisos} />
      </div>
      <Link href={esEstudiante ? "/portafolio" : "/docente/revision"} className={CLASE_ENLACE}>
        {esEstudiante ? "Ir a mi portafolio" : "Ir a la bandeja de revisión"}
      </Link>
    </div>
  );
}

function Cabecera({ nombre, estudianteId, esEstudiante }: { nombre: string | null; estudianteId: string; esEstudiante: boolean }) {
  return (
    <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">Mapa mental de competencias</p>
        <h1 className="text-2xl font-bold">{nombre ?? "Estudiante"}</h1>
        <p role="note" className="mt-1 text-sm">
          Basado solo en evaluaciones publicadas y validadas por el docente.
        </p>
      </div>
      <Link href={esEstudiante ? "/informe" : `/informe/${encodeURIComponent(estudianteId)}`} className="text-sm font-medium underline underline-offset-4">
        Ver informe integral
      </Link>
    </header>
  );
}

interface PropsContenido {
  estudianteId: string;
  esEstudiante: boolean;
  nombre: string | null;
}

function ContenidoMapa({ estudianteId, esEstudiante, nombre }: PropsContenido) {
  const cargar = useCallback(() => cargarMapa(estudianteId), [estudianteId]);
  const { estado, recargar } = useCarga(cargar);

  if (estado.tipo === "cargando") return <EsqueletoMapa mensaje={MENSAJE_GENERANDO_MAPA} />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar el mapa mental" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  const resultado = estado.datos;
  if (resultado.tipo === "denegado") return <SinPermiso mensaje={resultado.mensaje} />;
  if (resultado.tipo === "no_encontrado") return <NoEncontrado mensaje={resultado.mensaje} />;
  if (resultado.mapa.nodos.length === 0) {
    return <SinEvaluaciones nombre={nombre} esEstudiante={esEstudiante} avisos={resultado.mapa.avisos} />;
  }
  return (
    <div className="space-y-4">
      <Cabecera nombre={nombre} estudianteId={estudianteId} esEstudiante={esEstudiante} />
      <ListaAvisos avisos={resultado.mapa.avisos} />
      <ExploradorMapa mapa={resultado.mapa} nombre={nombre ?? estudianteId} />
    </div>
  );
}

/** Docente/admin: selector de estudiante y nombre tomado de GET /estudiantes (GET /usuarios es solo para admin). */
function ContenidoMapaDocente({ estudianteId }: { estudianteId: string }) {
  const { estado } = useListaEstudiantes();
  return (
    <div className="space-y-6">
      <SelectorEstudiante destino="mapa" actual={estudianteId} />
      <ContenidoMapa estudianteId={estudianteId} esEstudiante={false} nombre={nombreEnLista(estado, estudianteId)} />
    </div>
  );
}

/**
 * Mapa mental de un estudiante (RF-09). El estudiante solo puede ver el suyo; docente y admin, cualquiera.
 * Debe usarse dentro de GuardaRol (garantiza que hay perfil). El backend aplica el permiso real.
 */
export function VistaMapa({ estudianteId }: { estudianteId: string }) {
  const { perfil } = useSesion();
  if (!perfil) return null;
  if (perfil.rol !== "estudiante") return <ContenidoMapaDocente estudianteId={estudianteId} />;
  if (perfil.id !== estudianteId) return <SinPermiso mensaje="Solo puedes ver tu propio mapa mental." />;
  return <ContenidoMapa estudianteId={estudianteId} esEstudiante nombre={perfil.nombre} />;
}

/** /mapa: el estudiante ve el suyo; docente y admin eligen un estudiante. */
export function VistaMapaPropio() {
  const { perfil } = useSesion();
  if (!perfil) return null;
  if (perfil.rol !== "estudiante") return <ElegirEstudiante destino="mapa" />;
  return <ContenidoMapa estudianteId={perfil.id} esEstudiante nombre={perfil.nombre} />;
}
