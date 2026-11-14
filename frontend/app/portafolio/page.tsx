import type { Metadata } from "next";
import { PaginaProximamente } from "@/components/pagina-proximamente";

export const metadata: Metadata = { title: "Mi portafolio" };

export default function PaginaPortafolio() {
  return (
    <PaginaProximamente
      titulo="Mi portafolio"
      descripcion="Tus laboratorios por cohorte y el estado de cada entrega."
      roles={["estudiante"]}
    />
  );
}
