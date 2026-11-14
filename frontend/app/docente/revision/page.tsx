import type { Metadata } from "next";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaBandeja } from "@/components/revision/vista-bandeja";

export const metadata: Metadata = { title: "Revisión de evaluaciones" };

export default function PaginaBandejaRevision() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <GuardaRol roles={["docente", "admin"]}>
        <h1 className="text-3xl font-bold tracking-tight">Revisión de evaluaciones</h1>
        <p className="mt-2 text-muted-foreground">
          Revisa lo que propuso la IA, ajusta los niveles con un motivo, aprueba y publica. El estudiante solo ve las
          evaluaciones publicadas.
        </p>
        <VistaBandeja />
      </GuardaRol>
    </div>
  );
}
