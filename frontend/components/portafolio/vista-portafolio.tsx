"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { EstadoVacio, MensajeError } from "@/components/estados";
import { useSesion } from "@/components/proveedor-sesion";
import { TarjetaLaboratorio } from "@/components/portafolio/tarjeta-laboratorio";
import { ultimaEntregaPorLaboratorio } from "@/components/portafolio/estado-entrega";
import { evaluarEntrega, listarCohortes, listarEntregas, mensajeDeError } from "@/lib/api";
import type { Cohorte, Entrega } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

interface DatosPortafolio {
  cohortes: Cohorte[];
  entregas: Map<string, Entrega>;
}

type Aviso = { tipo: "exito" | "error"; mensaje: string; evaluacionId?: string };

function EsqueletoPortafolio() {
  return (
    <div role="status" aria-label="Cargando tu portafolio" className="mt-8 space-y-8">
      {[0, 1].map((seccion) => (
        <div key={seccion} className="space-y-3">
          <div className="h-6 w-40 animate-pulse rounded bg-muted" />
          {[0, 1].map((fila) => (
            <div key={fila} className="h-20 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ))}
      <span className="sr-only">Cargando tu portafolio…</span>
    </div>
  );
}

function AvisoAccion({ aviso }: { aviso: Aviso }) {
  const exito = aviso.tipo === "exito";
  return (
    <div
      role={exito ? "status" : "alert"}
      className={`mt-6 flex items-start gap-2 rounded-lg border p-3 text-sm ${
        exito ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-destructive/30 bg-destructive/5 text-destructive"
      }`}
    >
      {exito && <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />}
      <p>
        {aviso.mensaje}
        {aviso.evaluacionId && (
          <>
            {" "}
            <Link
              href={`/evaluaciones/${encodeURIComponent(aviso.evaluacionId)}`}
              className="font-medium underline underline-offset-4"
            >
              Ver progreso
            </Link>
          </>
        )}
      </p>
    </div>
  );
}

interface SeccionCohorteProps {
  cohorte: Cohorte;
  entregas: Map<string, Entrega>;
  evaluandoId: string | null;
  alEvaluar: (entregaId: string) => void;
}

function SeccionCohorte({ cohorte, entregas, evaluandoId, alEvaluar }: SeccionCohorteProps) {
  return (
    <section aria-labelledby={`cohorte-${cohorte.id}`} className="space-y-3">
      <h2 id={`cohorte-${cohorte.id}`} className="text-xl font-semibold">
        {cohorte.nombre}
      </h2>
      {cohorte.laboratorios.length === 0 ? (
        <p className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
          Esta cohorte todavía no tiene laboratorios.
        </p>
      ) : (
        <ul className="space-y-3">
          {cohorte.laboratorios.map((laboratorio) => {
            const entrega = entregas.get(laboratorio.id);
            return (
              <TarjetaLaboratorio
                key={laboratorio.id}
                laboratorio={laboratorio}
                entrega={entrega}
                evaluando={entrega !== undefined && evaluandoId === entrega.id}
                alEvaluar={alEvaluar}
              />
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function VistaPortafolio() {
  const { perfil } = useSesion();
  const estudianteId = perfil?.id;
  const [evaluandoId, setEvaluandoId] = useState<string | null>(null);
  const [aviso, setAviso] = useState<Aviso | null>(null);

  const cargar = useCallback(async (): Promise<DatosPortafolio> => {
    const [cohortes, entregas] = await Promise.all([listarCohortes(), listarEntregas(estudianteId)]);
    const ordenadas = [...cohortes].sort((a, b) => a.numero - b.numero);
    return { cohortes: ordenadas, entregas: ultimaEntregaPorLaboratorio(entregas) };
  }, [estudianteId]);

  const { estado, recargar, refrescar } = useCarga(cargar);

  const alEvaluar = useCallback(
    async (entregaId: string) => {
      setEvaluandoId(entregaId);
      setAviso(null);
      try {
        const { evaluacion_id: evaluacionId } = await evaluarEntrega(entregaId);
        setAviso({
          tipo: "exito",
          mensaje: "Tu entrega se envió a evaluación. Quedó pendiente de revisión docente: verás la nota cuando se publique.",
          evaluacionId,
        });
        refrescar();
      } catch (causa) {
        setAviso({ tipo: "error", mensaje: mensajeDeError(causa) });
      } finally {
        setEvaluandoId(null);
      }
    },
    [refrescar],
  );

  if (estado.tipo === "cargando") return <EsqueletoPortafolio />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar tu portafolio" mensaje={estado.mensaje} alReintentar={recargar} />;
  }

  const { cohortes, entregas } = estado.datos;
  if (cohortes.length === 0) {
    return (
      <EstadoVacio
        titulo="Aún no hay cohortes"
        mensaje="Cuando el docente registre las cohortes y sus laboratorios, aparecerán aquí."
      />
    );
  }

  return (
    <>
      {aviso && <AvisoAccion aviso={aviso} />}
      <div className="mt-8 space-y-10">
        {cohortes.map((cohorte) => (
          <SeccionCohorte
            key={cohorte.id}
            cohorte={cohorte}
            entregas={entregas}
            evaluandoId={evaluandoId}
            alEvaluar={(id) => void alEvaluar(id)}
          />
        ))}
      </div>
    </>
  );
}
