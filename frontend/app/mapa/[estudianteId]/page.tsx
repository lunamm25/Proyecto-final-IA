import type { Metadata } from "next";
import { Suspense } from "react";
import { GuardaRol } from "@/components/guarda-rol";
import { EsqueletoMapa } from "@/components/mapa/esqueleto-mapa";
import { VistaMapa } from "@/components/mapa/vista-mapa";

export const metadata: Metadata = { title: "Mapa mental de competencias" };

interface PropsMapa {
  params: Promise<{ estudianteId: string }>;
}

/** Lee el parámetro dinámico (en Next 16 `params` es una Promise) dentro de Suspense. */
async function ContenidoMapa({ params }: PropsMapa) {
  const { estudianteId } = await params;
  return <VistaMapa estudianteId={estudianteId} />;
}

export default function PaginaMapaEstudiante({ params }: PropsMapa) {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8">
      <Suspense fallback={<EsqueletoMapa />}>
        <GuardaRol roles={["estudiante", "docente", "admin"]}>
          <ContenidoMapa params={params} />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
