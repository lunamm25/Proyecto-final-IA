import type { Metadata } from "next";
import { PaginaProximamente } from "@/components/pagina-proximamente";

export const metadata: Metadata = { title: "Mapa mental de competencias" };

export default function PaginaMapa() {
  return (
    <PaginaProximamente
      titulo="Mapa mental de competencias"
      descripcion="Explora tus competencias en IA coloreadas por nivel de dominio."
      roles={["estudiante"]}
    />
  );
}
