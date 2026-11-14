import type { Metadata } from "next";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaConfigIA } from "@/components/docente/vista-config-ia";

export const metadata: Metadata = { title: "Configuración de IA" };

export default function PaginaConfigIA() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <GuardaRol roles={["docente", "admin"]}>
        <h1 className="text-3xl font-bold tracking-tight">Configuración de IA</h1>
        <p className="mt-2 text-muted-foreground">
          Elige el proveedor y el modelo que usará el asesor para evaluar las entregas.
        </p>
        <VistaConfigIA />
      </GuardaRol>
    </div>
  );
}
