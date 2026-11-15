import type { Metadata } from "next";
import { Suspense } from "react";
import { Cargando } from "@/components/estados";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaRevision } from "@/components/revision/vista-revision";

export const metadata: Metadata = { title: "Revisar evaluación" };

interface PropsRevision {
  params: Promise<{ id: string }>;
}

/** Lee el parámetro dinámico (en Next 16 `params` es una Promise) dentro de Suspense. */
async function ContenidoRevision({ params }: PropsRevision) {
  const { id } = await params;
  return <VistaRevision id={id} />;
}

export default function PaginaRevision({ params }: PropsRevision) {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <Suspense fallback={<Cargando texto="Cargando la evaluación…" />}>
        <GuardaRol roles={["docente", "admin"]}>
          <ContenidoRevision params={params} />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
