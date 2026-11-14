import type { Metadata } from "next";
import { PaginaProximamente } from "@/components/pagina-proximamente";

export const metadata: Metadata = { title: "Informe integral" };

export default function PaginaInforme() {
  return (
    <PaginaProximamente
      titulo="Informe integral"
      descripcion="Tu evolución, dominio por competencia y plan de fortalecimiento."
      roles={["estudiante"]}
    />
  );
}
