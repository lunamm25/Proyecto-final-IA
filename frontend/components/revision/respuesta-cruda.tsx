"use client";

import { useId, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { EventoTraza, JsonValor } from "@/lib/tipos";

const LINEAS_RESUMEN = 3;
const MAX_CARACTERES_RESUMEN = 240;
const CLAVE_CRUDAS = "respuestas_crudas";

type ObjetoJson = { [clave: string]: JsonValor };

function esObjeto(valor: JsonValor | null): valor is ObjetoJson {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

/** Respuestas crudas del modelo guardadas en `despues.respuestas_crudas` del evento (lista de textos). */
export function respuestasCrudasDe(evento: EventoTraza): string[] {
  if (!esObjeto(evento.despues)) return [];
  const lista = evento.despues[CLAVE_CRUDAS];
  return Array.isArray(lista) ? lista.filter((item): item is string => typeof item === "string") : [];
}

/** El mismo valor sin `respuestas_crudas`, para no volcar el texto largo dentro de la lista de eventos. */
export function sinRespuestasCrudas(valor: JsonValor | null): JsonValor | null {
  if (!esObjeto(valor) || !(CLAVE_CRUDAS in valor)) return valor;
  const resto = Object.fromEntries(Object.entries(valor).filter(([clave]) => clave !== CLAVE_CRUDAS));
  return Object.keys(resto).length > 0 ? resto : null;
}

/** Primeras líneas (y como máximo unos 240 caracteres) del texto, con "…" si se recortó. */
function resumir(texto: string): string {
  const lineas = texto.trim().split(/\r?\n/);
  let resumen = lineas.slice(0, LINEAS_RESUMEN).join("\n");
  if (resumen.length > MAX_CARACTERES_RESUMEN) resumen = resumen.slice(0, MAX_CARACTERES_RESUMEN);
  return resumen.length < texto.trim().length ? `${resumen.trimEnd()}…` : resumen;
}

const CLASE_PRE = "overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs whitespace-pre-wrap break-words";

/** Respuesta cruda de la IA colapsada: resumen corto visible y el texto completo al desplegar (RNF-03). */
export function RespuestaCruda({ respuestas }: { respuestas: string[] }) {
  const [abierta, setAbierta] = useState(false);
  const idContenido = useId();
  const varias = respuestas.length > 1;

  return (
    <div className="space-y-2 rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">
        {varias ? `${respuestas.length} intentos registrados. Resumen del último:` : "Resumen:"}
      </p>
      {!abierta && <pre className={CLASE_PRE}>{resumir(respuestas[respuestas.length - 1])}</pre>}
      {abierta && (
        <div id={idContenido} className="space-y-3">
          {respuestas.map((texto, indice) => (
            <div key={indice} className="space-y-1">
              {varias && <p className="text-xs font-medium">Intento {indice + 1}</p>}
              <pre className={`${CLASE_PRE} max-h-96 overflow-y-auto`}>{texto}</pre>
            </div>
          ))}
        </div>
      )}
      <Button type="button" variant="outline" size="sm" aria-expanded={abierta} aria-controls={abierta ? idContenido : undefined}
        onClick={() => setAbierta((previo) => !previo)}>
        {abierta ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}
        {abierta ? "Ocultar respuesta cruda" : "Ver respuesta cruda de la IA"}
      </Button>
    </div>
  );
}
