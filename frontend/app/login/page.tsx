import type { Metadata } from "next";
import { Suspense } from "react";
import { Cargando } from "@/components/estados";
import { FormularioAuth } from "@/components/formulario-auth";

export const metadata: Metadata = { title: "Iniciar sesión" };

export default function PaginaLogin() {
  return (
    <Suspense fallback={<Cargando />}>
      <FormularioAuth modo="login" />
    </Suspense>
  );
}
