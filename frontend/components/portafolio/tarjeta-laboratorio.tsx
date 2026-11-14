import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EtiquetaEstado } from "@/components/portafolio/etiqueta-estado";
import {
  estadoDeLaboratorio,
  formatearFecha,
  formatearNota,
  type EstadoLaboratorio,
} from "@/components/portafolio/estado-entrega";
import type { Entrega, IdNumerico, Laboratorio } from "@/lib/tipos";

interface TarjetaLaboratorioProps {
  laboratorio: Laboratorio;
  entrega: Entrega | undefined;
  evaluando: boolean;
  alEvaluar: (entregaId: IdNumerico) => void;
}

const CLASE_ENLACE_BOTON =
  "inline-flex h-8 items-center justify-center rounded-lg px-3 text-sm font-medium transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 outline-none";

interface AccionesProps {
  estado: EstadoLaboratorio;
  laboratorio: Laboratorio;
  entrega: Entrega | undefined;
  evaluando: boolean;
  alEvaluar: (entregaId: IdNumerico) => void;
}

function Acciones({ estado, laboratorio, entrega, evaluando, alEvaluar }: AccionesProps) {
  const rutaEntregar = `/portafolio/${laboratorio.id}/entregar`;

  if (estado === "sin_entregar" || !entrega) {
    return (
      <Link href={rutaEntregar} className={`${CLASE_ENLACE_BOTON} bg-primary text-primary-foreground hover:bg-primary/80`}>
        Entregar
      </Link>
    );
  }

  if (estado === "sin_evaluar" || estado === "error") {
    return (
      <>
        <Button onClick={() => alEvaluar(entrega.id)} disabled={evaluando} aria-busy={evaluando}>
          {evaluando && <Loader2 className="animate-spin" aria-hidden="true" />}
          {estado === "error" ? "Evaluar de nuevo" : "Evaluar"}
        </Button>
        <Link href={rutaEntregar} className={`${CLASE_ENLACE_BOTON} border hover:bg-muted`}>
          Nueva entrega
        </Link>
      </>
    );
  }

  if (estado === "publicada" && entrega.evaluacion) {
    return (
      <Link
        href={`/evaluaciones/${entrega.evaluacion.id}`}
        className={`${CLASE_ENLACE_BOTON} border hover:bg-muted`}
      >
        Ver evaluación
      </Link>
    );
  }

  return (
    <>
      <p className="text-xs text-muted-foreground">El docente revisará la evaluación antes de publicarla.</p>
      {entrega.evaluacion && (
        <Link
          href={`/evaluaciones/${entrega.evaluacion.id}`}
          className={`${CLASE_ENLACE_BOTON} border hover:bg-muted`}
        >
          Ver progreso
        </Link>
      )}
    </>
  );
}

export function TarjetaLaboratorio({ laboratorio, entrega, evaluando, alEvaluar }: TarjetaLaboratorioProps) {
  const estado = estadoDeLaboratorio(entrega);
  const nota = estado === "publicada" ? entrega?.evaluacion?.nota ?? null : null;

  return (
    <li className="flex flex-col gap-3 rounded-xl border bg-card p-4 md:flex-row md:items-center md:gap-6">
      <div className="min-w-0 flex-1">
        <p className="font-mono text-xs text-muted-foreground">{laboratorio.codigo}</p>
        <h3 className="font-semibold">{laboratorio.titulo}</h3>
        {entrega && (
          <p className="mt-1 text-xs text-muted-foreground">Entregado el {formatearFecha(entrega.creada_en)}</p>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3 md:w-72">
        <EtiquetaEstado estado={estado} />
        {nota !== null && (
          <span className="text-sm">
            Nota: <strong className="text-base">{formatearNota(nota)}</strong>
            <span className="text-muted-foreground"> / 5,0</span>
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2 md:w-56 md:justify-end">
        <Acciones
          estado={estado}
          laboratorio={laboratorio}
          entrega={entrega}
          evaluando={evaluando}
          alEvaluar={alEvaluar}
        />
      </div>
    </li>
  );
}
