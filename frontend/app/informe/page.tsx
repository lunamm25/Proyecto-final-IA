import type { Metadata } from "next";
import { Suspense } from "react";
import { GuardaRol } from "@/components/guarda-rol";
import { EsqueletoInforme } from "@/components/informe/esqueleto-informe";
import { VistaInformePropio } from "@/components/informe/vista-informe";

export const metadata: Metadata = { title: "Informe integral" };

export default function PaginaInforme() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 print:max-w-none print:p-0">
      <Suspense fallback={<EsqueletoInforme />}>
        <GuardaRol roles={["estudiante"]}>
          <VistaInformePropio />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
