import type { Metadata } from "next";
import { Suspense } from "react";
import { Cargando } from "@/components/estados";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaEntregar } from "@/components/portafolio/vista-entregar";

export const metadata: Metadata = { title: "Entregar laboratorio" };

interface PropsEntregar {
  params: Promise<{ labId: string }>;
}

/** Lee el parámetro dinámico (en Next 16 `params` es una Promise) dentro de Suspense. */
async function ContenidoEntregar({ params }: PropsEntregar) {
  const { labId } = await params;
  return <VistaEntregar labId={labId} />;
}

export default function PaginaEntregar({ params }: PropsEntregar) {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <Suspense fallback={<Cargando texto="Cargando el laboratorio…" />}>
        <GuardaRol roles={["estudiante"]}>
          <ContenidoEntregar params={params} />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
