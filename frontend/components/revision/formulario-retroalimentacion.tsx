"use client";

import { useId, useState } from "react";
import { Loader2, Pencil, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Campo, CLASE_CONTROL } from "@/components/docente/campo";
import {
  MAX_MOTIVO_EDICION,
  cambiosCriterio,
  cambiosGenerales,
  errorMotivo,
  formularioCriterio,
  formularioGeneral,
  type CampoCriterio,
  type CampoGeneral,
  type Errores,
} from "@/components/revision/modelo-retroalimentacion";
import { editarRetroalimentacion, mensajeDeError } from "@/lib/api";
import type { Evaluacion, EvaluacionCriterio, IdNumerico, RetroalimentacionEntrada } from "@/lib/tipos";

interface DefinicionCampo<C extends string> {
  campo: C;
  etiqueta: string;
  filas: number;
  lista?: boolean;
}

const CAMPOS_GENERALES: DefinicionCampo<CampoGeneral>[] = [
  { campo: "retroalimentacion_general", etiqueta: "Retroalimentación general", filas: 4 },
  { campo: "como_aplico_conocimientos", etiqueta: "Cómo aplicó los conocimientos", filas: 3 },
  { campo: "aprendizajes_identificados", etiqueta: "Aprendizajes identificados", filas: 4, lista: true },
  { campo: "aspectos_a_fortalecer", etiqueta: "Aspectos a fortalecer", filas: 4, lista: true },
];

const CAMPOS_CRITERIO: DefinicionCampo<CampoCriterio>[] = [
  { campo: "justificacion", etiqueta: "Justificación", filas: 3 },
  { campo: "fortalezas", etiqueta: "Fortalezas", filas: 3, lista: true },
  { campo: "debilidades", etiqueta: "Debilidades", filas: 3, lista: true },
  { campo: "recomendacion", etiqueta: "Recomendación", filas: 3 },
];

type Envio = { tipo: "inactivo" } | { tipo: "enviando" } | { tipo: "error"; mensaje: string };

interface FormularioTextosProps<C extends string> {
  titulo: string;
  campos: DefinicionCampo<C>[];
  valores: Record<C, string>;
  errores: Errores<C>;
  motivo: string;
  envio: Envio;
  alCambiar: (campo: C, valor: string) => void;
  alCambiarMotivo: (valor: string) => void;
  alEnviar: () => void;
  alCancelar: () => void;
}

/** Formulario común: un textarea por campo (las listas, una por línea) y motivo opcional. */
function FormularioTextos<C extends string>(props: FormularioTextosProps<C>) {
  const base = useId();
  const enviando = props.envio.tipo === "enviando";
  return (
    <form noValidate onSubmit={(e) => { e.preventDefault(); props.alEnviar(); }}
      className="space-y-3 rounded-lg border border-dashed p-3">
      <h4 className="text-sm font-semibold">{props.titulo}</h4>
      {props.campos.map(({ campo, etiqueta, filas, lista }) => (
        <Campo key={campo} id={`${base}-${campo}`} etiqueta={etiqueta} error={props.errores[campo]}
          ayuda={lista ? "Un elemento por línea." : undefined}>
          {(a11y) => (
            <textarea {...a11y} rows={filas} value={props.valores[campo]} disabled={enviando} className={CLASE_CONTROL}
              onChange={(e) => props.alCambiar(campo, e.target.value)} />
          )}
        </Campo>
      ))}
      <Campo id={`${base}-motivo`} etiqueta="Motivo de la edición (opcional)" error={props.errores.motivo}
        ayuda={`Queda en la auditoría. Máximo ${MAX_MOTIVO_EDICION} caracteres.`}>
        {(a11y) => (
          <input {...a11y} value={props.motivo} disabled={enviando} className={CLASE_CONTROL}
            onChange={(e) => props.alCambiarMotivo(e.target.value)} />
        )}
      </Campo>
      {props.errores.general && <p role="alert" className="text-sm text-destructive">{props.errores.general}</p>}
      {props.envio.tipo === "error" && <p role="alert" className="text-sm text-destructive">{props.envio.mensaje}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={enviando} aria-busy={enviando}>
          {enviando && <Loader2 className="animate-spin" aria-hidden="true" />}
          Guardar textos
        </Button>
        <Button type="button" variant="outline" disabled={enviando} onClick={props.alCancelar}>Cancelar</Button>
      </div>
    </form>
  );
}

/** Estado y envío compartidos por ambos editores. */
function useEnvioRetro(evaluacionId: IdNumerico, alGuardar: (evaluacion: Evaluacion) => void, alTerminar: () => void) {
  const [envio, setEnvio] = useState<Envio>({ tipo: "inactivo" });
  async function enviar(entrada: RetroalimentacionEntrada) {
    setEnvio({ tipo: "enviando" });
    try {
      alGuardar(await editarRetroalimentacion(evaluacionId, entrada));
      setEnvio({ tipo: "inactivo" });
      alTerminar();
    } catch (causa) {
      setEnvio({ tipo: "error", mensaje: mensajeDeError(causa) });
    }
  }
  return { envio, enviar };
}

interface AccionesCerradoProps {
  textoEditar: string;
  alAbrir: () => void;
  /** null = no hay texto original de la IA para restablecer. */
  alRestablecer: (() => void) | null;
  envio: Envio;
}

/** Botones del editor cerrado: editar y, si hay texto de la IA, restablecerlo (envía null). */
function AccionesCerrado({ textoEditar, alAbrir, alRestablecer, envio }: AccionesCerradoProps) {
  const enviando = envio.tipo === "enviando";
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" size="sm" onClick={alAbrir} disabled={enviando}>
          <Pencil aria-hidden="true" />
          {textoEditar}
        </Button>
        {alRestablecer && (
          <Button type="button" variant="ghost" size="sm" onClick={alRestablecer} disabled={enviando} aria-busy={enviando}>
            {enviando ? <Loader2 className="animate-spin" aria-hidden="true" /> : <RotateCcw aria-hidden="true" />}
            Restablecer texto de la IA
          </Button>
        )}
      </div>
      {envio.tipo === "error" && <p role="alert" className="text-sm text-destructive">{envio.mensaje}</p>}
    </div>
  );
}

const PREGUNTA_RESTABLECER =
  "¿Restablecer el texto propuesto por la IA? Se descartarán las ediciones hechas a estos textos (queda registrado en la traza).";

/** Pide el motivo opcional y confirma antes de restablecer. Devuelve null si se cancela. */
function confirmarRestablecer(): { motivo?: string } | null {
  if (!window.confirm(PREGUNTA_RESTABLECER)) return null;
  const motivo = window.prompt("Motivo (opcional):", "")?.trim().slice(0, MAX_MOTIVO_EDICION) ?? "";
  return motivo ? { motivo } : {};
}

interface EditorGeneralProps {
  evaluacion: Evaluacion;
  /** Motivo por el que no se puede editar (estado aprobada/publicada); null si se puede. */
  bloqueo: string | null;
  alGuardar: (evaluacion: Evaluacion) => void;
}

/** Edita la retroalimentación general (RF-07 CA2). Los textos originales de la IA se conservan en el backend. */
export function EditorRetroGeneral({ evaluacion, bloqueo, alGuardar }: EditorGeneralProps) {
  const [abierto, setAbierto] = useState(false);
  const [valores, setValores] = useState(() => formularioGeneral(evaluacion.retroalimentacion));
  const [motivo, setMotivo] = useState("");
  const [errores, setErrores] = useState<Errores<CampoGeneral>>({});
  const { envio, enviar } = useEnvioRetro(evaluacion.id, alGuardar, () => setAbierto(false));

  if (bloqueo) return null;
  if (!abierto) {
    const restablecer = () => {
      const confirmacion = confirmarRestablecer();
      if (!confirmacion) return;
      void enviar({
        retroalimentacion_general: null,
        como_aplico_conocimientos: null,
        aprendizajes_identificados: null,
        aspectos_a_fortalecer: null,
        ...confirmacion,
      });
    };
    return (
      <AccionesCerrado textoEditar="Editar retroalimentación general" envio={envio}
        alRestablecer={evaluacion.retroalimentacion_ia ? restablecer : null}
        alAbrir={() => {
          setValores(formularioGeneral(evaluacion.retroalimentacion));
          setMotivo("");
          setErrores({});
          setAbierto(true);
        }} />
    );
  }

  function guardar() {
    const { cambios, errores: nuevos } = cambiosGenerales(valores, evaluacion.retroalimentacion);
    const errorDelMotivo = errorMotivo(motivo);
    if (errorDelMotivo) nuevos.motivo = errorDelMotivo;
    if (Object.keys(nuevos).length === 0 && Object.keys(cambios).length === 0) nuevos.general = "No cambiaste ningún texto.";
    setErrores(nuevos);
    if (Object.keys(nuevos).length > 0) return;
    void enviar({ ...cambios, ...(motivo.trim() ? { motivo: motivo.trim() } : {}) });
  }

  return (
    <FormularioTextos titulo="Editar retroalimentación general" campos={CAMPOS_GENERALES} valores={valores}
      errores={errores} motivo={motivo} envio={envio}
      alCambiar={(campo, valor) => setValores((v) => ({ ...v, [campo]: valor }))}
      alCambiarMotivo={setMotivo} alEnviar={guardar} alCancelar={() => setAbierto(false)} />
  );
}

interface EditorCriterioProps {
  evaluacionId: IdNumerico;
  criterio: EvaluacionCriterio;
  bloqueo: string | null;
  alGuardar: (evaluacion: Evaluacion) => void;
}

/** Edita los textos de un criterio (justificación, fortalezas, debilidades y recomendación). */
export function EditorRetroCriterio({ evaluacionId, criterio, bloqueo, alGuardar }: EditorCriterioProps) {
  const [abierto, setAbierto] = useState(false);
  const [valores, setValores] = useState(() => formularioCriterio(criterio));
  const [motivo, setMotivo] = useState("");
  const [errores, setErrores] = useState<Errores<CampoCriterio>>({});
  const { envio, enviar } = useEnvioRetro(evaluacionId, alGuardar, () => setAbierto(false));

  if (bloqueo) return null;
  if (!abierto) {
    const restablecer = () => {
      const confirmacion = confirmarRestablecer();
      if (!confirmacion) return;
      void enviar({
        criterios: [
          { criterio_id: criterio.criterio_id, justificacion: null, fortalezas: null, debilidades: null, recomendacion: null },
        ],
        ...confirmacion,
      });
    };
    return (
      <AccionesCerrado textoEditar="Editar textos del criterio" envio={envio}
        alRestablecer={criterio.original_ia ? restablecer : null}
        alAbrir={() => {
          setValores(formularioCriterio(criterio));
          setMotivo("");
          setErrores({});
          setAbierto(true);
        }} />
    );
  }

  function guardar() {
    const { cambios, hayCambios, errores: nuevos } = cambiosCriterio(valores, criterio);
    const errorDelMotivo = errorMotivo(motivo);
    if (errorDelMotivo) nuevos.motivo = errorDelMotivo;
    if (Object.keys(nuevos).length === 0 && !hayCambios) nuevos.general = "No cambiaste ningún texto.";
    setErrores(nuevos);
    if (Object.keys(nuevos).length > 0) return;
    void enviar({ criterios: [cambios], ...(motivo.trim() ? { motivo: motivo.trim() } : {}) });
  }

  return (
    <FormularioTextos titulo="Editar textos del criterio" campos={CAMPOS_CRITERIO} valores={valores}
      errores={errores} motivo={motivo} envio={envio}
      alCambiar={(campo, valor) => setValores((v) => ({ ...v, [campo]: valor }))}
      alCambiarMotivo={setMotivo} alEnviar={guardar} alCancelar={() => setAbierto(false)} />
  );
}
