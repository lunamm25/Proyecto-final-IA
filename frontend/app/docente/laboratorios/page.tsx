import type { Metadata } from "next";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaLaboratorios } from "@/components/docente/vista-laboratorios";

export const metadata: Metadata = { title: "Laboratorios y rúbricas" };

export default function PaginaLaboratorios() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <GuardaRol roles={["docente", "admin"]}>
        <h1 className="text-3xl font-bold tracking-tight">Laboratorios y rúbricas</h1>
        <p className="mt-2 text-muted-foreground">
          Crea y edita los laboratorios de cada cohorte. Cada laboratorio debe tener una rúbrica vigente (versión
          aprobada) para poder evaluar sus entregas.
        </p>
        <VistaLaboratorios />
      </GuardaRol>
    </div>
  );
}
