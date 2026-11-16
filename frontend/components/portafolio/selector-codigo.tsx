"use client";

import { CampoArchivo } from "@/components/portafolio/campo-archivo";
import {
  MAX_ZIP_MB,
  validarZip,
  type CampoEntrega,
  type DatosFormulario,
  type ErroresEntrega,
} from "@/components/portafolio/validacion-entrega";

interface SelectorCodigoProps {
  datos: DatosFormulario;
  errores: ErroresEntrega;
  deshabilitado: boolean;
  alActualizar: (cambios: Partial<DatosFormulario>, campo: CampoEntrega, error?: string) => void;
}

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
        URL del repositorio de GitHub <span className="font-normal text-muted-foreground">(opcional)</span>
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

/** Código del laboratorio: ZIP y URL de GitHub, los dos opcionales. Se envía solo lo que tenga valor. */
export function SelectorCodigo({ datos, errores, deshabilitado, alActualizar }: SelectorCodigoProps) {
  return (
    <fieldset className="space-y-4 rounded-xl border p-4">
      <legend className="px-1 text-sm font-medium">
        Código del laboratorio <span className="font-normal text-muted-foreground">(opcional)</span>
      </legend>
      <CampoArchivo
        id="zip"
        etiqueta="Archivo ZIP con el código (opcional)"
        ayuda={`Solo .zip, máximo ${MAX_ZIP_MB} MB. El servidor también limita el número de archivos y el tamaño descomprimido.`}
        accept=".zip,application/zip,application/x-zip-compressed"
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
      <CampoGithub
        valor={datos.githubUrl}
        error={errores.github_url}
        deshabilitado={deshabilitado}
        alCambiar={(githubUrl) => alActualizar({ githubUrl }, "github_url")}
      />
    </fieldset>
  );
}
