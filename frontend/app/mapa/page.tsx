import type { Metadata } from "next";
import { Suspense } from "react";
import { GuardaRol } from "@/components/guarda-rol";
import { EsqueletoMapa } from "@/components/mapa/esqueleto-mapa";
import { VistaMapaPropio } from "@/components/mapa/vista-mapa";

export const metadata: Metadata = { title: "Mapa mental de competencias" };

export default function PaginaMapa() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8">
      <Suspense fallback={<EsqueletoMapa />}>
        <GuardaRol roles={["estudiante"]}>
          <VistaMapaPropio />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
