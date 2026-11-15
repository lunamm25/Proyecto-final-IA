import type { Metadata } from "next";
import { Suspense } from "react";
import { Cargando } from "@/components/estados";
import { FormularioAuth } from "@/components/formulario-auth";

export const metadata: Metadata = { title: "Crear cuenta" };

export default function PaginaRegistro() {
  return (
    <Suspense fallback={<Cargando />}>
      <FormularioAuth modo="registro" />
    </Suspense>
  );
}
