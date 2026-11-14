"use client";

import { useCallback, useState } from "react";
import { CheckCircle2, Info, TriangleAlert, XCircle } from "lucide-react";
import { Cargando, MensajeError } from "@/components/estados";
import type { DatosAviso } from "@/components/docente/aviso";
import { FormularioConfigIA } from "@/components/docente/formulario-config-ia";
import {
  aEntrada,
  aFormulario,
  etiquetaProveedor,
  formatearTemperatura,
  hayCambios,
  limpiarConfig,
  modeloSugerido,
  proveedorPermitido,
  validarConfig,
  type FormularioConfig,
} from "@/components/docente/modelo-config-ia";
import { PruebaConexion } from "@/components/docente/prueba-conexion";
import { useAvisoSalida } from "@/components/rubricas/use-aviso-salida";
import { useSesion } from "@/components/proveedor-sesion";
import { guardarConfigIA, mensajeDeError, obtenerConfigIA } from "@/lib/api";
import { formatearFechaHora } from "@/lib/fechas";
import { nombreVisible } from "@/lib/perfil";
import type { ClavesIA, ConfigIA, ProveedorIA } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

const CLASE_TARJETA = "rounded-xl border bg-card p-5";

function NotaSeguridad() {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-sky-300 bg-sky-50 p-3 text-sm text-sky-900">
      <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-1">
        <p>
          La URL base y las claves de API se configuran en las variables de entorno del servidor y nunca se muestran
          aquí: solo se indica si están configuradas.
        </p>
        <p>
          Cada evaluación guarda el proveedor, el modelo, la temperatura y la versión del prompt con que se generó,
          así que cambiar esta configuración no altera las evaluaciones anteriores.
        </p>
      </div>
    </div>
  );
}

function useNombreActualizador(config: ConfigIA): string {
  const { perfil } = useSesion();
  const actor = config.actualizado_por;
  if (!actor) return config.origen === "entorno" ? "Valores por defecto del servidor" : "Sin registro";
  const nombre = nombreVisible(actor.nombre, "Usuario sin nombre");
  return perfil?.id === actor.id ? `${nombre} (tú)` : nombre;
}

function ConfigActual({ config }: { config: ConfigIA }) {
  const actualizadoPor = useNombreActualizador(config);
  const filas: [string, string][] = [
    ["Proveedor", etiquetaProveedor(config, config.proveedor)],
    ["Modelo", config.modelo],
    ["Temperatura", formatearTemperatura(config.temperatura)],
    ["Actualizada por", actualizadoPor],
    ["Última actualización", config.actualizado_en ? formatearFechaHora(config.actualizado_en) : "Sin registro"],
  ];
  return (
    <section aria-labelledby="titulo-config-actual" className={CLASE_TARJETA}>
      <h2 id="titulo-config-actual" className="text-lg font-semibold">Configuración vigente</h2>
      <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
        {filas.map(([etiqueta, valor]) => (
          <div key={etiqueta} className="contents">
            <dt className="text-muted-foreground">{etiqueta}</dt>
            <dd className="font-medium break-words">{valor}</dd>
          </div>
        ))}
      </dl>
      {!config.modelo_permitido && (
        <p role="alert" className="mt-3 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          El modelo vigente ya no está en la lista de modelos permitidos. Elige otro y guarda.
        </p>
      )}
    </section>
  );
}

const TEXTO_CLAVE: Record<keyof ClavesIA, string> = {
  gemini_api_key_configurada: "Clave de API de Gemini",
  openai_compat_api_key_configurada: "Clave de API OpenAI-compatible",
  openai_compat_base_url_configurada: "URL base OpenAI-compatible",
};

/** Estado de los secretos del servidor: solo sí/no (el backend nunca envía los valores). */
function EstadoClaves({ claves }: { claves: ClavesIA }) {
  return (
    <section aria-labelledby="titulo-claves" className={CLASE_TARJETA}>
      <h2 id="titulo-claves" className="text-lg font-semibold">Claves del servidor</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {(Object.keys(TEXTO_CLAVE) as (keyof ClavesIA)[]).map((clave) => {
          const configurada = claves[clave];
          const Icono = configurada ? CheckCircle2 : XCircle;
          return (
            <li key={clave} className="flex items-center justify-between gap-3">
              <span>{TEXTO_CLAVE[clave]}</span>
              <span className={`inline-flex items-center gap-1 font-medium ${configurada ? "text-emerald-800" : "text-destructive"}`}>
                <Icono className="size-4" aria-hidden="true" />
                {configurada ? "Configurada" : "No configurada"}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** Versiones de los prompts que usa el backend (solo lectura). */
function VersionesPrompt({ versiones }: { versiones: Record<string, string | null> }) {
  const entradas = Object.entries(versiones);
  return (
    <section aria-labelledby="titulo-prompts" className={CLASE_TARJETA}>
      <h2 id="titulo-prompts" className="text-lg font-semibold">Versiones de los prompts</h2>
      {entradas.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">El servidor no informó versiones de prompts.</p>
      ) : (
        <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
          {entradas.map(([nombre, version]) => (
            <div key={nombre} className="contents">
              <dt className="font-mono text-xs text-muted-foreground">{nombre}</dt>
              <dd className="font-medium">{version ?? "Sin versión"}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function EditorConfig({ inicial, alGuardada }: { inicial: ConfigIA; alGuardada: (config: ConfigIA) => void }) {
  const [guardada, setGuardada] = useState(inicial);
  const [formulario, setFormulario] = useState<FormularioConfig>(() => aFormulario(inicial));
  const [intentado, setIntentado] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<DatosAviso | null>(null);
  const cambios = hayCambios(formulario, guardada);
  const errores = intentado ? validarConfig(formulario, guardada) : {};
  useAvisoSalida(cambios);

  const cambiar = useCallback((cambio: Partial<FormularioConfig>) => {
    setFormulario((previo) => ({ ...previo, ...cambio }));
    setAviso(null);
  }, []);

  /** Al cambiar de proveedor, el selector muestra sus modelos y se elige uno válido (el probado primero). */
  const cambiarProveedor = (proveedor: ProveedorIA) => {
    const actualValido = proveedorPermitido(guardada, proveedor)?.modelos.includes(formulario.modelo) ?? false;
    cambiar({ proveedor, modelo: actualValido ? formulario.modelo : modeloSugerido(proveedorPermitido(guardada, proveedor)) });
  };

  async function guardar() {
    setIntentado(true);
    setAviso(null);
    if (Object.keys(validarConfig(formulario, guardada)).length > 0) return;
    setGuardando(true);
    try {
      const nueva = limpiarConfig(await guardarConfigIA(aEntrada(formulario)));
      setGuardada(nueva);
      setFormulario(aFormulario(nueva));
      setIntentado(false);
      setAviso({ tipo: "exito", mensaje: "Configuración guardada. Las próximas evaluaciones usarán este modelo." });
      alGuardada(nueva);
    } catch (causa) {
      setAviso({ tipo: "error", mensaje: mensajeDeError(causa) });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
      <div className={CLASE_TARJETA}>
        <FormularioConfigIA config={guardada} formulario={formulario} errores={errores} cambios={cambios}
          guardando={guardando} aviso={aviso} alGuardar={() => void guardar()} alCambiar={cambiar}
          alCambiarProveedor={cambiarProveedor}
          alDescartar={() => { setFormulario(aFormulario(guardada)); setIntentado(false); setAviso(null); }} />
      </div>
      <div className={CLASE_TARJETA}>
        <PruebaConexion key={guardada.actualizado_en ?? "inicial"} guardada={guardada} cambiosSinGuardar={cambios} />
      </div>
    </div>
  );
}

async function cargarConfig(): Promise<ConfigIA> {
  return limpiarConfig(await obtenerConfigIA());
}

/** Pantalla de RF-10 (solo admin): configuración vigente, claves, prompts, cambio de modelo y prueba de conexión. */
export function VistaConfigIA() {
  const { estado, recargar } = useCarga(cargarConfig);
  const [actual, setActual] = useState<ConfigIA | null>(null);

  if (estado.tipo === "cargando") return <Cargando texto="Cargando la configuración de IA…" />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar la configuración de IA" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  const config = actual ?? estado.datos;

  return (
    <div className="mt-8 space-y-6">
      <NotaSeguridad />
      <div className="grid gap-6 lg:grid-cols-2">
        <ConfigActual config={config} />
        <EstadoClaves claves={config.claves} />
      </div>
      <EditorConfig inicial={estado.datos} alGuardada={setActual} />
      <VersionesPrompt versiones={config.versiones_prompt} />
    </div>
  );
}
