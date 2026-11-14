"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Aviso, type DatosAviso } from "@/components/docente/aviso";
import { Campo, CLASE_CONTROL } from "@/components/docente/campo";
import {
  MAX_MODELO,
  OPCIONES_PROVEEDOR,
  PASO_TEMPERATURA,
  SUGERENCIAS_MODELO,
  TEMPERATURA_MAXIMA,
  TEMPERATURA_MINIMA,
  type ErroresConfig,
  type FormularioConfig,
} from "@/components/docente/modelo-config-ia";
import type { ProveedorIA } from "@/lib/tipos";

interface FormularioConfigIAProps {
  formulario: FormularioConfig;
  errores: ErroresConfig;
  cambios: boolean;
  guardando: boolean;
  aviso: DatosAviso | null;
  alCambiar: (cambio: Partial<FormularioConfig>) => void;
  alGuardar: () => void;
  alDescartar: () => void;
}

function SelectorProveedor({ valor, deshabilitado, alCambiar }: {
  valor: ProveedorIA;
  deshabilitado: boolean;
  alCambiar: (proveedor: ProveedorIA) => void;
}) {
  return (
    <fieldset className="space-y-2" disabled={deshabilitado}>
      <legend className="text-sm font-medium">Proveedor <span className="text-destructive">*</span></legend>
      {OPCIONES_PROVEEDOR.map((opcion) => (
        <label key={opcion.valor}
          className="flex cursor-pointer items-start gap-3 rounded-lg border p-3 has-checked:border-primary has-checked:bg-primary/5 has-focus-visible:ring-3 has-focus-visible:ring-ring/50">
          <input type="radio" name="proveedor" value={opcion.valor} checked={valor === opcion.valor}
            aria-describedby={`proveedor-${opcion.valor}-desc`} className="mt-1"
            onChange={() => alCambiar(opcion.valor)} />
          <span>
            <span className="block text-sm font-medium">{opcion.etiqueta}</span>
            <span id={`proveedor-${opcion.valor}-desc`} className="block text-xs text-muted-foreground">
              {opcion.descripcion}
            </span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}

function CampoModelo({ formulario, error, deshabilitado, alCambiar }: {
  formulario: FormularioConfig;
  error?: string;
  deshabilitado: boolean;
  alCambiar: (modelo: string) => void;
}) {
  return (
    <Campo id="config-modelo" etiqueta="Modelo" obligatorio error={error}
      ayuda="Elige una sugerencia o escribe el nombre exacto del modelo que ofrece tu proveedor.">
      {(a11y) => (
        <>
          <input {...a11y} list="sugerencias-modelo" value={formulario.modelo} maxLength={MAX_MODELO}
            disabled={deshabilitado} autoComplete="off" spellCheck={false} className={CLASE_CONTROL}
            onChange={(e) => alCambiar(e.target.value)} />
          <datalist id="sugerencias-modelo">
            {SUGERENCIAS_MODELO[formulario.proveedor].map((modelo) => (
              <option key={modelo} value={modelo} />
            ))}
          </datalist>
        </>
      )}
    </Campo>
  );
}

function CampoTemperatura({ valor, error, deshabilitado, alCambiar }: {
  valor: string;
  error?: string;
  deshabilitado: boolean;
  alCambiar: (temperatura: string) => void;
}) {
  return (
    <Campo id="config-temperatura" etiqueta="Temperatura" obligatorio error={error}
      ayuda="Cualquier valor entre 0 y 0,2. Un valor bajo hace que las evaluaciones sean reproducibles.">
      {(a11y) => (
        <input {...a11y} type="number" inputMode="decimal" min={TEMPERATURA_MINIMA} max={TEMPERATURA_MAXIMA}
          step={PASO_TEMPERATURA} value={valor} disabled={deshabilitado} className={`${CLASE_CONTROL} sm:max-w-40`}
          onChange={(e) => alCambiar(e.target.value)} />
      )}
    </Campo>
  );
}

/** Formulario de RF-10: proveedor, modelo y temperatura. No hay campos de URL ni de clave. */
export function FormularioConfigIA(props: FormularioConfigIAProps) {
  const { formulario, errores, cambios, guardando, aviso, alCambiar, alGuardar, alDescartar } = props;

  function enviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    alGuardar();
  }

  return (
    <form onSubmit={enviar} noValidate aria-labelledby="titulo-form-config" className="space-y-5">
      <h2 id="titulo-form-config" className="text-lg font-semibold">Cambiar configuración</h2>
      <SelectorProveedor valor={formulario.proveedor} deshabilitado={guardando}
        alCambiar={(proveedor) => alCambiar({ proveedor })} />
      <CampoModelo formulario={formulario} error={errores.modelo} deshabilitado={guardando}
        alCambiar={(modelo) => alCambiar({ modelo })} />
      <CampoTemperatura valor={formulario.temperatura} error={errores.temperatura} deshabilitado={guardando}
        alCambiar={(temperatura) => alCambiar({ temperatura })} />
      <p aria-live="polite" className="text-sm text-amber-800">
        {cambios ? "Tienes cambios sin guardar." : ""}
      </p>
      {aviso && <Aviso tipo={aviso.tipo} mensaje={aviso.mensaje} />}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button type="button" variant="outline" disabled={!cambios || guardando} onClick={alDescartar}>
          Descartar cambios
        </Button>
        <Button type="submit" disabled={!cambios || guardando} aria-busy={guardando}>
          {guardando && <Loader2 className="animate-spin" aria-hidden="true" />}
          {guardando ? "Guardando…" : "Guardar"}
        </Button>
      </div>
    </form>
  );
}
