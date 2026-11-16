import type { Metadata } from "next";
import { Suspense } from "react";
import { Cargando } from "@/components/estados";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaEvaluacion } from "@/components/evaluaciones/vista-evaluacion";

export const metadata: Metadata = { title: "Evaluación" };

interface PropsEvaluacion {
  params: Promise<{ id: string }>;
}

/** Lee el parámetro dinámico (en Next 16 `params` es una Promise) dentro de Suspense. */
async function ContenidoEvaluacion({ params }: PropsEvaluacion) {
  const { id } = await params;
  return <VistaEvaluacion id={id} />;
}

export default function PaginaEvaluacion({ params }: PropsEvaluacion) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-10">
      <Suspense fallback={<Cargando texto="Cargando la evaluación…" />}>
        <GuardaRol roles={["estudiante", "docente", "admin"]}>
          <ContenidoEvaluacion params={params} />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
