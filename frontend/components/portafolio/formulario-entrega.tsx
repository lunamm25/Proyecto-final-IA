"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Info, Loader2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CampoArchivo } from "@/components/portafolio/campo-archivo";
import { SelectorCodigo } from "@/components/portafolio/selector-codigo";
import {
  MAX_PDF_MB,
  ORDEN_CAMPOS,
  fuentesElegidas,
  validarFormulario,
  validarPdf,
  type CampoEntrega,
  type DatosFormulario,
  type ErroresEntrega,
  type ModoCodigo,
} from "@/components/portafolio/validacion-entrega";
import { crearEntrega, mensajeDeError } from "@/lib/api";
import type { IdNumerico, NuevaEntrega } from "@/lib/tipos";

const ESPERA_REDIRECCION_MS = 3000;

interface FormularioEntregaProps {
  laboratorioId: IdNumerico;
  versionRubrica: number;
}

const DATOS_INICIALES: DatosFormulario = { pdf: null, modoCodigo: "zip", zip: null, githubUrl: "" };

/** Cuerpo de POST /entregas: laboratorio_id y solo las fuentes elegidas (al menos una, ya validado). */
function construirEntrega(laboratorioId: IdNumerico, datos: DatosFormulario): NuevaEntrega {
  const { pdf, zip, github } = fuentesElegidas(datos);
  const entrega: NuevaEntrega = { laboratorio_id: laboratorioId };
  if (pdf) entrega.pdf = pdf;
  if (zip) entrega.zip = zip;
  if (github) entrega.github_url = github;
  return entrega;
}

/** Eligió GitHub y no adjuntó PDF (con GitHub elegido, el ZIP no se envía). */
function soloGithub(datos: DatosFormulario): boolean {
  return datos.modoCodigo === "github" && !datos.pdf;
}

/**
 * El backend no clona repositorios: una entrega solo con la URL de GitHub termina en error al evaluar.
 * Es un aviso (no bloquea el envío).
 */
function AvisoSoloGithub() {
  return (
    <div role="status" className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p>
        Para que la IA pueda evaluar tu código, adjunta también el PDF del informe o el ZIP del código. Solo con la URL de
        GitHub la evaluación terminará en error.
      </p>
    </div>
  );
}

function MensajeExito() {
  return (
    <div role="status" className="rounded-xl border border-emerald-300 bg-emerald-50 p-6 text-emerald-900">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
        <div>
          <h2 className="font-semibold">¡Entrega enviada!</h2>
          <p className="mt-1 text-sm">
            Tu entrega quedó registrada. Desde tu portafolio puedes enviarla a evaluación. Te llevaremos allí en unos
            segundos.
          </p>
          <Link href="/portafolio" className="mt-3 inline-block text-sm font-medium underline underline-offset-4">
            Volver a mi portafolio
          </Link>
        </div>
      </div>
    </div>
  );
}

/** Formulario de entrega (RF-04): PDF, código (ZIP o GitHub), o ambos; al menos uno. */
export function FormularioEntrega({ laboratorioId, versionRubrica }: FormularioEntregaProps) {
  const router = useRouter();
  const [datos, setDatos] = useState<DatosFormulario>(DATOS_INICIALES);
  const [errores, setErrores] = useState<ErroresEntrega>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [enviada, setEnviada] = useState(false);

  useEffect(() => {
    if (!enviada) return;
    const temporizador = setTimeout(() => router.push("/portafolio"), ESPERA_REDIRECCION_MS);
    return () => clearTimeout(temporizador);
  }, [enviada, router]);

  const actualizar = (cambios: Partial<DatosFormulario>, campo: CampoEntrega, error?: string) => {
    setDatos((previos) => ({ ...previos, ...cambios }));
    setErrores((previos) => ({ ...previos, [campo]: error, fuentes: undefined }));
  };

  const cambiarModo = (modoCodigo: ModoCodigo) => {
    setDatos((previos) => ({ ...previos, modoCodigo }));
    setErrores((previos) => ({ ...previos, zip: undefined, github_url: undefined }));
  };

  const enfocarPrimerError = (encontrados: ErroresEntrega) => {
    const campo = ORDEN_CAMPOS.find((nombre) => encontrados[nombre]);
    if (campo) document.getElementById(campo === "fuentes" ? "pdf" : campo)?.focus();
  };

  const alEnviar = async (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setErrorGeneral(null);
    const encontrados = validarFormulario(datos);
    setErrores(encontrados);
    if (Object.keys(encontrados).length > 0) {
      enfocarPrimerError(encontrados);
      return;
    }
    setEnviando(true);
    try {
      await crearEntrega(construirEntrega(laboratorioId, datos));
      setEnviada(true);
    } catch (causa) {
      // 413, 422 y 503 traen `detail` en español: se muestra tal cual.
      setErrorGeneral(mensajeDeError(causa));
    } finally {
      setEnviando(false);
    }
  };

  if (enviada) return <MensajeExito />;

  return (
    <form noValidate onSubmit={(evento) => void alEnviar(evento)} className="space-y-6" aria-describedby="nota-entrega">
      <p className="text-sm text-muted-foreground">
        Adjunta al menos uno: el informe en PDF, el código en ZIP o la URL de GitHub.
      </p>
      {errores.fuentes && (
        <p id="fuentes-error" role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {errores.fuentes}
        </p>
      )}

      <CampoArchivo
        id="pdf"
        etiqueta="Informe del laboratorio (PDF)"
        ayuda={`Solo .pdf, máximo ${MAX_PDF_MB} MB. Debe tener texto seleccionable (no un escaneo como imagen).`}
        accept="application/pdf,.pdf"
        error={errores.pdf}
        deshabilitado={enviando}
        archivos={datos.pdf ? [datos.pdf] : []}
        alElegir={(archivos) => {
          const pdf = archivos[0] ?? null;
          const error = validarPdf(pdf);
          actualizar({ pdf: error ? null : pdf }, "pdf", error);
        }}
        alQuitar={() => actualizar({ pdf: null }, "pdf")}
      />

      <SelectorCodigo
        datos={datos}
        errores={errores}
        deshabilitado={enviando}
        alCambiarModo={cambiarModo}
        alActualizar={actualizar}
      />

      {soloGithub(datos) && <AvisoSoloGithub />}

      <div id="nota-entrega" className="flex items-start gap-2 rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <p>
          La entrega quedará asociada a la <strong>versión {versionRubrica}</strong> de la rúbrica vigente. El servidor
          también revisa los archivos (por ejemplo, rechaza un PDF sin texto extraíble o un ZIP demasiado grande).
        </p>
      </div>

      {errorGeneral && (
        <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <p className="font-medium">No se pudo enviar la entrega.</p>
          <p>{errorGeneral}</p>
        </div>
      )}

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Link
          href="/portafolio"
          className="inline-flex h-9 items-center justify-center rounded-lg border px-4 text-sm font-medium outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          Cancelar
        </Link>
        <Button type="submit" size="lg" disabled={enviando} aria-busy={enviando} className="px-4">
          {enviando && <Loader2 className="animate-spin" aria-hidden="true" />}
          {enviando ? "Enviando…" : "Enviar entrega"}
        </Button>
      </div>
    </form>
  );
}
