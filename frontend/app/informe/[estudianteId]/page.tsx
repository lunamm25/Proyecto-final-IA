import type { Metadata } from "next";
import { Suspense } from "react";
import { GuardaRol } from "@/components/guarda-rol";
import { EsqueletoInforme } from "@/components/informe/esqueleto-informe";
import { VistaInforme } from "@/components/informe/vista-informe";

export const metadata: Metadata = { title: "Informe integral" };

interface PropsInforme {
  params: Promise<{ estudianteId: string }>;
}

/** Lee el parámetro dinámico (en Next 16 `params` es una Promise) dentro de Suspense. */
async function ContenidoInforme({ params }: PropsInforme) {
  const { estudianteId } = await params;
  return <VistaInforme estudianteId={estudianteId} />;
}

export default function PaginaInformeEstudiante({ params }: PropsInforme) {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 print:max-w-none print:p-0">
      <Suspense fallback={<EsqueletoInforme />}>
        <GuardaRol roles={["estudiante", "docente", "admin"]}>
          <ContenidoInforme params={params} />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
