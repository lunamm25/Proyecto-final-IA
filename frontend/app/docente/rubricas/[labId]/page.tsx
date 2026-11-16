import type { Metadata } from "next";
import { Suspense } from "react";
import { Cargando } from "@/components/estados";
import { GuardaRol } from "@/components/guarda-rol";
import { VistaEditorRubrica } from "@/components/rubricas/vista-editor-rubrica";

export const metadata: Metadata = { title: "Editar rúbrica" };

interface PropsRubrica {
  params: Promise<{ labId: string }>;
}

/** Lee el parámetro dinámico (en Next 16 `params` es una Promise) dentro de Suspense. */
async function ContenidoRubrica({ params }: PropsRubrica) {
  const { labId } = await params;
  return <VistaEditorRubrica labId={labId} />;
}

export default function PaginaRubrica({ params }: PropsRubrica) {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10">
      <Suspense fallback={<Cargando texto="Cargando la rúbrica…" />}>
        <GuardaRol roles={["docente", "admin"]}>
          <ContenidoRubrica params={params} />
        </GuardaRol>
      </Suspense>
    </div>
  );
}
