"use client";

import { cn } from "@/lib/utils";
import { CampoArchivo } from "@/components/portafolio/campo-archivo";
import {
  MAX_ZIP_MB,
  validarZip,
  type CampoEntrega,
  type DatosFormulario,
  type ErroresEntrega,
  type ModoCodigo,
} from "@/components/portafolio/validacion-entrega";

interface SelectorCodigoProps {
  datos: DatosFormulario;
  errores: ErroresEntrega;
  deshabilitado: boolean;
  alCambiarModo: (modo: ModoCodigo) => void;
  alActualizar: (cambios: Partial<DatosFormulario>, campo: CampoEntrega, error?: string) => void;
}

const OPCIONES: { valor: ModoCodigo; texto: string }[] = [
  { valor: "zip", texto: "Archivo ZIP" },
  { valor: "github", texto: "URL de GitHub" },
];

interface CampoGithubProps {
  valor: string;
  error?: string;
  deshabilitado: boolean;
  alCambiar: (valor: string) => void;
}

function CampoGithub({ valor, error, deshabilitado, alCambiar }: CampoGithubProps) {
  return (
    <div className="space-y-2">
      <label htmlFor="github_url" className="text-sm font-medium">
        URL del repositorio <span className="text-destructive">*</span>
      </label>
      <p id="github_url-ayuda" className="text-xs text-muted-foreground">
        Repositorio público con la forma https://github.com/usuario/repositorio.
      </p>
      <input
        id="github_url"
        name="github_url"
        type="url"
        inputMode="url"
        autoComplete="url"
        placeholder="https://github.com/usuario/repositorio"
        value={valor}
        disabled={deshabilitado}
        aria-required
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? "github_url-ayuda github_url-error" : "github_url-ayuda"}
        onChange={(evento) => alCambiar(evento.target.value)}
        className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive disabled:opacity-50"
      />
      {error && (
        <p id="github_url-error" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

/** Código del laboratorio: exactamente una opción, ZIP o URL pública de GitHub (RF-04 CA1). */
export function SelectorCodigo({
  datos,
  errores,
  deshabilitado,
  alCambiarModo,
  alActualizar,
}: SelectorCodigoProps) {
  return (
    <fieldset className="space-y-4 rounded-xl border p-4">
      <legend className="px-1 text-sm font-medium">
        Código del laboratorio <span className="text-destructive">*</span>
      </legend>
      <div className="flex flex-col gap-2 sm:flex-row sm:gap-6">
        {OPCIONES.map((opcion) => (
          <label
            key={opcion.valor}
            className={cn(
              "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm",
              datos.modoCodigo === opcion.valor && "border-primary bg-muted/60",
            )}
          >
            <input
              type="radio"
              name="modo_codigo"
              value={opcion.valor}
              checked={datos.modoCodigo === opcion.valor}
              disabled={deshabilitado}
              onChange={() => alCambiarModo(opcion.valor)}
              className="accent-primary"
            />
            {opcion.texto}
          </label>
        ))}
      </div>

      {datos.modoCodigo === "zip" ? (
        <CampoArchivo
          id="zip"
          etiqueta="Archivo ZIP con el código"
          ayuda={`Solo .zip, máximo ${MAX_ZIP_MB} MB. El servidor también limita el número de archivos y el tamaño descomprimido.`}
          accept=".zip,application/zip,application/x-zip-compressed"
          obligatorio
          error={errores.zip}
          deshabilitado={deshabilitado}
          archivos={datos.zip ? [datos.zip] : []}
          alElegir={(archivos) => {
            const zip = archivos[0] ?? null;
            const error = validarZip(zip);
            alActualizar({ zip: error ? null : zip }, "zip", error);
          }}
          alQuitar={() => alActualizar({ zip: null }, "zip")}
        />
      ) : (
        <CampoGithub
          valor={datos.githubUrl}
          error={errores.github_url}
          deshabilitado={deshabilitado}
          alCambiar={(githubUrl) => alActualizar({ githubUrl }, "github_url")}
        />
      )}
    </fieldset>
  );
}
