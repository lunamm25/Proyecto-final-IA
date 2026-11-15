"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Aviso, type DatosAviso } from "@/components/docente/aviso";
import { Campo, CLASE_CONTROL } from "@/components/docente/campo";
import {
  PASO_TEMPERATURA,
  TEMPERATURA_MINIMA,
  estaProbado,
  formatearTemperatura,
  proveedorPermitido,
  temperaturaMaxima,
  type ErroresConfig,
  type FormularioConfig,
} from "@/components/docente/modelo-config-ia";
import type { ConfigIA, ProveedorIA } from "@/lib/tipos";

interface FormularioConfigIAProps {
  /** Configuración del backend: de aquí salen proveedores, modelos y temperatura máxima. */
  config: ConfigIA;
  formulario: FormularioConfig;
  errores: ErroresConfig;
  cambios: boolean;
  guardando: boolean;
  aviso: DatosAviso | null;
  alCambiarProveedor: (proveedor: ProveedorIA) => void;
  alCambiar: (cambio: Partial<FormularioConfig>) => void;
  alGuardar: () => void;
  alDescartar: () => void;
}

function SelectorProveedor({ config, valor, error, deshabilitado, alCambiar }: {
  config: ConfigIA;
  valor: ProveedorIA;
  error?: string;
  deshabilitado: boolean;
  alCambiar: (proveedor: ProveedorIA) => void;
}) {
  return (
    <fieldset className="space-y-2" disabled={deshabilitado} aria-describedby={error ? "proveedor-error" : undefined}>
      <legend className="text-sm font-medium">Proveedor <span className="text-destructive">*</span></legend>
      {config.proveedores_permitidos.map((opcion) => (
        <label key={opcion.proveedor}
          className="flex cursor-pointer items-start gap-3 rounded-lg border p-3 has-checked:border-primary has-checked:bg-primary/5 has-focus-visible:ring-3 has-focus-visible:ring-ring/50">
          <input type="radio" name="proveedor" value={opcion.proveedor} checked={valor === opcion.proveedor}
            className="mt-1" onChange={() => alCambiar(opcion.proveedor)} />
          <span>
            <span className="block text-sm font-medium">{opcion.etiqueta}</span>
            <span className="block text-xs text-muted-foreground">
              {opcion.modelos.length === 0
                ? "El servidor no tiene modelos permitidos para este proveedor."
                : `${opcion.modelos.length} ${opcion.modelos.length === 1 ? "modelo permitido" : "modelos permitidos"}`}
            </span>
          </span>
        </label>
      ))}
      {error && <p id="proveedor-error" className="text-sm text-destructive">{error}</p>}
    </fieldset>
  );
}

function CampoModelo({ config, formulario, error, deshabilitado, alCambiar }: {
  config: ConfigIA;
  formulario: FormularioConfig;
  error?: string;
  deshabilitado: boolean;
  alCambiar: (modelo: string) => void;
}) {
  const permitido = proveedorPermitido(config, formulario.proveedor);
  const modelos = permitido?.modelos ?? [];
  const sinProbar = formulario.modelo !== "" && modelos.includes(formulario.modelo) && !estaProbado(permitido, formulario.modelo);
  return (
    <Campo id="config-modelo" etiqueta="Modelo" obligatorio error={error}
      ayuda="Solo se pueden elegir los modelos que permite el servidor. «Sin probar»: aún no se ha validado con nuestros prompts.">
      {(a11y) => (
        <div className="space-y-2">
          <select {...a11y} value={modelos.includes(formulario.modelo) ? formulario.modelo : ""}
            disabled={deshabilitado || modelos.length === 0} className={CLASE_CONTROL}
            onChange={(e) => alCambiar(e.target.value)}>
            <option value="" disabled>{modelos.length === 0 ? "No hay modelos disponibles" : "Elige un modelo…"}</option>
            {modelos.map((modelo) => (
              <option key={modelo} value={modelo}>
                {modelo}{estaProbado(permitido, modelo) ? "" : " (sin probar)"}
              </option>
            ))}
          </select>
          {sinProbar && (
            <p className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
              Este modelo está sin probar: puede que sus respuestas no siempre cumplan el formato esperado.
            </p>
          )}
        </div>
      )}
    </Campo>
  );
}

function CampoTemperatura({ valor, maxima, error, deshabilitado, alCambiar }: {
  valor: string;
  maxima: number;
  error?: string;
  deshabilitado: boolean;
  alCambiar: (temperatura: string) => void;
}) {
  return (
    <Campo id="config-temperatura" etiqueta="Temperatura" obligatorio error={error}
      ayuda={`Cualquier valor entre 0 y ${formatearTemperatura(maxima)}. Un valor bajo hace que las evaluaciones sean reproducibles.`}>
      {(a11y) => (
        <input {...a11y} type="number" inputMode="decimal" min={TEMPERATURA_MINIMA} max={maxima}
          step={PASO_TEMPERATURA} value={valor} disabled={deshabilitado} className={`${CLASE_CONTROL} sm:max-w-40`}
          onChange={(e) => alCambiar(e.target.value)} />
      )}
    </Campo>
  );
}

/** Formulario de RF-10: proveedor, modelo y temperatura. No hay campos de URL ni de clave. */
export function FormularioConfigIA(props: FormularioConfigIAProps) {
  const { config, formulario, errores, cambios, guardando, aviso, alCambiarProveedor, alCambiar, alGuardar, alDescartar } = props;

  function enviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    alGuardar();
  }

  return (
    <form onSubmit={enviar} noValidate aria-labelledby="titulo-form-config" className="space-y-5">
      <h2 id="titulo-form-config" className="text-lg font-semibold">Cambiar configuración</h2>
      <SelectorProveedor config={config} valor={formulario.proveedor} error={errores.proveedor} deshabilitado={guardando}
        alCambiar={alCambiarProveedor} />
      <CampoModelo config={config} formulario={formulario} error={errores.modelo} deshabilitado={guardando}
        alCambiar={(modelo) => alCambiar({ modelo })} />
      <CampoTemperatura valor={formulario.temperatura} maxima={temperaturaMaxima(config)} error={errores.temperatura}
        deshabilitado={guardando} alCambiar={(temperatura) => alCambiar({ temperatura })} />
      <p aria-live="polite" className="text-sm text-amber-800">
        {cambios ? "Tienes cambios sin guardar." : ""}
      </p>
      {aviso && <Aviso tipo={aviso.tipo} mensaje={aviso.mensaje} />}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
        <p id="ayuda-guardar-config" className="text-xs text-muted-foreground sm:mr-auto">
          El cambio solo afecta a las evaluaciones nuevas; las anteriores conservan su configuración.
        </p>
        <div className="flex flex-col-reverse gap-2 sm:flex-row">
          <Button type="button" variant="outline" disabled={!cambios || guardando} onClick={alDescartar}>
            Descartar cambios
          </Button>
          <Button type="submit" disabled={!cambios || guardando} aria-busy={guardando} aria-describedby="ayuda-guardar-config">
            {guardando && <Loader2 className="animate-spin" aria-hidden="true" />}
            {guardando ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </form>
  );
}
