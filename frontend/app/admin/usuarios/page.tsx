import type { Metadata } from "next";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaUsuarios } from "@/components/admin/vista-usuarios";

export const metadata: Metadata = { title: "Gestión de usuarios" };

export default function PaginaUsuarios() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <GuardaRol roles={["admin"]}>
        <h1 className="text-3xl font-bold tracking-tight">Gestión de usuarios</h1>
        <p className="mt-2 text-muted-foreground">
          Consulta los usuarios registrados y cambia su rol. Todo usuario nuevo empieza como estudiante.
        </p>
        <VistaUsuarios />
      </GuardaRol>
    </div>
  );
}
