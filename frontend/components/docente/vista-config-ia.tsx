"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { Cargando, MensajeError } from "@/components/estados";
import type { DatosAviso } from "@/components/docente/aviso";
import { FormularioConfigIA } from "@/components/docente/formulario-config-ia";
import {
  TEXTO_PROVEEDOR,
  aEntrada,
  aFormulario,
  formatearTemperatura,
  hayCambios,
  limpiarConfig,
  validarConfig,
  type FormularioConfig,
} from "@/components/docente/modelo-config-ia";
import { PruebaConexion } from "@/components/docente/prueba-conexion";
import { formatearFechaHora } from "@/components/evaluaciones/estado-evaluacion";
import { useAvisoSalida } from "@/components/rubricas/use-aviso-salida";
import { useSesion } from "@/components/proveedor-sesion";
import { guardarConfigIA, listarUsuarios, mensajeDeError, obtenerConfigIA } from "@/lib/api";
import type { ConfigIA } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

interface DatosConfig {
  config: ConfigIA;
  /** id → nombre, para mostrar quién actualizó (vacío si no se pudo consultar). */
  nombres: Record<string, string>;
}

/** `actualizado_por` es un id: se intenta resolver el nombre con GET /usuarios; si falla, se omite. */
async function cargarNombres(): Promise<Record<string, string>> {
  try {
    const usuarios = await listarUsuarios();
    return Object.fromEntries(usuarios.map((usuario) => [usuario.id, usuario.nombre]));
  } catch {
    return {};
  }
}

async function cargarDatos(): Promise<DatosConfig> {
  const [config, nombres] = await Promise.all([obtenerConfigIA(), cargarNombres()]);
  return { config: limpiarConfig(config), nombres };
}

const CLASE_TARJETA = "rounded-xl border bg-card p-5";

function NotaSeguridad() {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-sky-300 bg-sky-50 p-3 text-sm text-sky-900">
      <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-1">
        <p>
          La URL base y la clave de API se configuran en las variables de entorno del servidor y nunca se muestran
          aquí.
        </p>
        <p>
          Cada evaluación guarda el proveedor, el modelo, la temperatura y la versión del prompt con que se generó,
          así que cambiar esta configuración no altera las evaluaciones anteriores.
        </p>
      </div>
    </div>
  );
}

function ConfigActual({ config, actualizadoPor }: { config: ConfigIA; actualizadoPor: string }) {
  const filas: [string, string][] = [
    ["Proveedor", TEXTO_PROVEEDOR[config.proveedor]],
    ["Modelo", config.modelo],
    ["Temperatura", formatearTemperatura(config.temperatura)],
    ["Actualizada por", actualizadoPor],
    ["Última actualización", config.actualizado_en ? formatearFechaHora(config.actualizado_en) : "Sin registro"],
  ];
  return (
    <section aria-labelledby="titulo-config-actual" className={CLASE_TARJETA}>
      <h2 id="titulo-config-actual" className="text-lg font-semibold">Configuración guardada</h2>
      <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
        {filas.map(([etiqueta, valor]) => (
          <div key={etiqueta} className="contents">
            <dt className="text-muted-foreground">{etiqueta}</dt>
            <dd className="font-medium break-words">{valor}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function useNombreActualizador(datos: DatosConfig | null): string {
  const { perfil } = useSesion();
  const id = datos?.config.actualizado_por ?? null;
  if (!id) return "Sin registro";
  if (perfil?.id === id) return `${perfil.nombre} (tú)`;
  return datos?.nombres[id] ?? "Usuario no identificado";
}

function EditorConfig({ inicial, alGuardada }: { inicial: ConfigIA; alGuardada: (config: ConfigIA) => void }) {
  const [guardada, setGuardada] = useState(inicial);
  const [formulario, setFormulario] = useState<FormularioConfig>(() => aFormulario(inicial));
  const [intentado, setIntentado] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<DatosAviso | null>(null);
  const cambios = hayCambios(formulario, guardada);
  const errores = intentado ? validarConfig(formulario) : {};
  useAvisoSalida(cambios);

  async function guardar() {
    setIntentado(true);
    setAviso(null);
    if (Object.keys(validarConfig(formulario)).length > 0) return;
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
        <FormularioConfigIA formulario={formulario} errores={errores} cambios={cambios} guardando={guardando}
          aviso={aviso} alGuardar={() => void guardar()}
          alCambiar={(cambio) => { setFormulario((previo) => ({ ...previo, ...cambio })); setAviso(null); }}
          alDescartar={() => { setFormulario(aFormulario(guardada)); setIntentado(false); setAviso(null); }} />
      </div>
      <div className={CLASE_TARJETA}>
        <PruebaConexion key={guardada.actualizado_en ?? "inicial"} guardada={guardada} cambiosSinGuardar={cambios} />
      </div>
    </div>
  );
}

/** Pantalla de RF-10: muestra la configuración guardada, permite cambiarla y probar la conexión. */
export function VistaConfigIA() {
  const { estado, recargar } = useCarga(cargarDatos);
  const [actual, setActual] = useState<ConfigIA | null>(null);
  const datos = estado.tipo === "listo" ? { ...estado.datos, config: actual ?? estado.datos.config } : null;
  const actualizadoPor = useNombreActualizador(datos);

  if (estado.tipo === "cargando") return <Cargando texto="Cargando la configuración de IA…" />;
  if (estado.tipo === "error" || !datos) {
    return (
      <MensajeError titulo="No se pudo cargar la configuración de IA"
        mensaje={estado.tipo === "error" ? estado.mensaje : ""} alReintentar={recargar} />
    );
  }

  return (
    <div className="mt-8 space-y-6">
      <NotaSeguridad />
      <ConfigActual config={datos.config} actualizadoPor={actualizadoPor} />
      <EditorConfig inicial={estado.datos.config} alGuardada={setActual} />
    </div>
  );
}
