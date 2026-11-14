"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Aviso } from "@/components/docente/aviso";
import { Campo, CLASE_CONTROL } from "@/components/docente/campo";
import {
  LABORATORIO_VACIO,
  MAX_CODIGO,
  MAX_TITULO,
  limpiarLaboratorio,
  validarLaboratorio,
  type CampoLaboratorio,
} from "@/components/docente/validacion-laboratorio";
import { actualizarLaboratorio, crearLaboratorio, mensajeDeError } from "@/lib/api";
import type { Cohorte, Laboratorio, LaboratorioEntrada } from "@/lib/tipos";

interface DialogoLaboratorioProps {
  /** null = crear un laboratorio nuevo. */
  laboratorio: Laboratorio | null;
  cohortes: Cohorte[];
  alCerrar: () => void;
  alGuardar: (laboratorio: Laboratorio) => void;
}

function datosIniciales(laboratorio: Laboratorio | null, cohortes: Cohorte[]): LaboratorioEntrada {
  if (!laboratorio) return { ...LABORATORIO_VACIO, cohorte_id: cohortes.length === 1 ? cohortes[0].id : "" };
  return {
    cohorte_id: laboratorio.cohorte_id,
    codigo: laboratorio.codigo,
    titulo: laboratorio.titulo,
    descripcion: laboratorio.descripcion,
    objetivos: laboratorio.objetivos,
  };
}

/** Diálogo modal nativo (<dialog>): atrapa el foco y se cierra con Escape. */
export function DialogoLaboratorio({ laboratorio, cohortes, alCerrar, alGuardar }: DialogoLaboratorioProps) {
  const refDialogo = useRef<HTMLDialogElement>(null);
  const [datos, setDatos] = useState<LaboratorioEntrada>(() => datosIniciales(laboratorio, cohortes));
  const [intentado, setIntentado] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const errores = intentado ? validarLaboratorio(datos, cohortes, laboratorio?.id ?? null) : {};
  const titulo = laboratorio ? `Editar ${laboratorio.codigo}` : "Nuevo laboratorio";

  useEffect(() => {
    refDialogo.current?.showModal();
  }, []);

  function cambiar(campo: CampoLaboratorio, valor: string) {
    setDatos((previo) => ({ ...previo, [campo]: valor }));
  }

  async function guardar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setIntentado(true);
    setErrorServidor(null);
    if (Object.keys(validarLaboratorio(datos, cohortes, laboratorio?.id ?? null)).length > 0) return;
    setGuardando(true);
    try {
      const limpio = limpiarLaboratorio(datos);
      alGuardar(laboratorio ? await actualizarLaboratorio(laboratorio.id, limpio) : await crearLaboratorio(limpio));
    } catch (causa) {
      setErrorServidor(mensajeDeError(causa));
      setGuardando(false);
    }
  }

  return (
    <dialog
      ref={refDialogo}
      aria-labelledby="titulo-dialogo-laboratorio"
      onClose={alCerrar}
      onCancel={(evento) => guardando && evento.preventDefault()}
      className="m-auto w-[calc(100%-2rem)] max-w-xl rounded-xl border bg-background p-0 text-foreground shadow-xl backdrop:bg-black/40"
    >
      <form onSubmit={guardar} noValidate className="max-h-[85vh] space-y-4 overflow-y-auto p-6">
        <div className="flex items-start justify-between gap-4">
          <h2 id="titulo-dialogo-laboratorio" className="text-lg font-semibold">
            {titulo}
          </h2>
          <Button type="button" variant="ghost" size="icon-sm" aria-label="Cerrar" disabled={guardando} onClick={alCerrar}>
            <X aria-hidden="true" />
          </Button>
        </div>
        <CamposLaboratorio datos={datos} errores={errores} cohortes={cohortes} deshabilitado={guardando} alCambiar={cambiar} />
        {errorServidor && <Aviso tipo="error" mensaje={errorServidor} />}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" disabled={guardando} onClick={alCerrar}>
            Cancelar
          </Button>
          <Button type="submit" disabled={guardando}>
            {guardando && <Loader2 className="animate-spin" aria-hidden="true" />}
            {guardando ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </form>
    </dialog>
  );
}

interface CamposLaboratorioProps {
  datos: LaboratorioEntrada;
  errores: Partial<Record<CampoLaboratorio, string>>;
  cohortes: Cohorte[];
  deshabilitado: boolean;
  alCambiar: (campo: CampoLaboratorio, valor: string) => void;
}

function CamposLaboratorio({ datos, errores, cohortes, deshabilitado, alCambiar }: CamposLaboratorioProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Campo id="lab-cohorte" etiqueta="Cohorte" obligatorio error={errores.cohorte_id}>
        {(a11y) => (
          <select {...a11y} value={datos.cohorte_id} disabled={deshabilitado} className={CLASE_CONTROL}
            onChange={(e) => alCambiar("cohorte_id", e.target.value)}>
            <option value="">Elige una cohorte…</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
        )}
      </Campo>
      <Campo id="lab-codigo" etiqueta="Código" obligatorio ayuda="Único dentro de la cohorte, p. ej. C2-L1." error={errores.codigo}>
        {(a11y) => (
          <input {...a11y} value={datos.codigo} maxLength={MAX_CODIGO} disabled={deshabilitado} className={CLASE_CONTROL}
            onChange={(e) => alCambiar("codigo", e.target.value)} />
        )}
      </Campo>
      <Campo id="lab-titulo" etiqueta="Título" obligatorio error={errores.titulo} className="sm:col-span-2">
        {(a11y) => (
          <input {...a11y} value={datos.titulo} maxLength={MAX_TITULO} disabled={deshabilitado} className={CLASE_CONTROL}
            onChange={(e) => alCambiar("titulo", e.target.value)} />
        )}
      </Campo>
      <Campo id="lab-descripcion" etiqueta="Descripción" obligatorio error={errores.descripcion} className="sm:col-span-2">
        {(a11y) => (
          <textarea {...a11y} rows={3} value={datos.descripcion} disabled={deshabilitado} className={CLASE_CONTROL}
            onChange={(e) => alCambiar("descripcion", e.target.value)} />
        )}
      </Campo>
      <Campo id="lab-objetivos" etiqueta="Objetivos" obligatorio ayuda="Escribe un objetivo por línea."
        error={errores.objetivos} className="sm:col-span-2">
        {(a11y) => (
          <textarea {...a11y} rows={4} value={datos.objetivos} disabled={deshabilitado} className={CLASE_CONTROL}
            onChange={(e) => alCambiar("objetivos", e.target.value)} />
        )}
      </Campo>
    </div>
  );
}
