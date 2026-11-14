import type { Metadata } from "next";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaPortafolio } from "@/components/portafolio/vista-portafolio";

export const metadata: Metadata = { title: "Mi portafolio" };

export default function PaginaPortafolio() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <GuardaRol roles={["estudiante"]}>
        <h1 className="text-3xl font-bold tracking-tight">Mi portafolio</h1>
        <p className="mt-2 text-muted-foreground">
          Tus laboratorios por cohorte y el estado de cada entrega. La nota solo aparece cuando el docente publica la
          evaluación.
        </p>
        <VistaPortafolio />
      </GuardaRol>
    </div>
  );
}
