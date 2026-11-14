import type { Metadata } from "next";
import { PaginaProximamente } from "@/components/pagina-proximamente";

export const metadata: Metadata = { title: "Panel docente" };

export default function PaginaDocente() {
  return (
    <PaginaProximamente
      titulo="Panel docente"
      descripcion="Gestiona laboratorios, rúbricas, evaluaciones y la configuración de IA."
      roles={["docente", "admin"]}
    />
  );
}
