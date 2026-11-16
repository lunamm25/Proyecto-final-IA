"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { imprimirInforme } from "@/components/informe/use-impresion";

export function BotonDescargarPdf({ nombreEstudiante }: { nombreEstudiante: string }) {
  return (
    <div className="flex flex-col items-start gap-1 sm:items-end print:hidden">
      <Button onClick={() => imprimirInforme(nombreEstudiante)} aria-describedby="ayuda-pdf">
        <Download aria-hidden="true" />
        Descargar PDF
      </Button>
      <p id="ayuda-pdf" className="text-xs text-muted-foreground">
        Se abrirá el diálogo de impresión: elige «Guardar como PDF».
      </p>
    </div>
  );
}
