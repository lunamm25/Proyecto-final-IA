import type { Metadata } from "next";
import { GuardaRol } from "@/components/guarda-rol";
import { PanelDocente } from "@/components/docente/panel-docente";

export const metadata: Metadata = { title: "Panel docente" };

export default function PaginaDocente() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10">
      <GuardaRol roles={["docente", "admin"]}>
        <PanelDocente />
      </GuardaRol>
    </div>
  );
}
