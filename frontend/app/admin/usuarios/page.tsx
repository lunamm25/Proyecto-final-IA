import type { Metadata } from "next";
import { PaginaProximamente } from "@/components/pagina-proximamente";

export const metadata: Metadata = { title: "Gestión de usuarios" };

export default function PaginaUsuarios() {
  return (
    <PaginaProximamente
      titulo="Gestión de usuarios"
      descripcion="Consulta los usuarios y cambia su rol."
      roles={["admin"]}
    />
  );
}
