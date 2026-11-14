// Estado del editor de rúbricas y conversiones con el contrato (`Rubrica`, §7). Funciones puras.
import type { CriterioBorrador, NivelBorrador } from "@/lib/inconsistencias-rubrica";
import type { Rubrica } from "@/lib/tipos";

/** `clave` es interna del editor (para React y los ids de los campos); no se envía al backend. */
export interface NivelEditor extends NivelBorrador {
  clave: string;
}

export interface CriterioEditor extends Omit<CriterioBorrador, "niveles"> {
  clave: string;
  niveles: NivelEditor[];
}

export interface RubricaEditor {
  titulo: string;
  criterios: CriterioEditor[];
}

let contadorClaves = 0;

function nuevaClave(): string {
  contadorClaves += 1;
  return `k${contadorClaves}`;
}

export function nuevoNivel(): NivelEditor {
  return { clave: nuevaClave(), nombre: "", puntaje: null, descriptor: "" };
}

/** Criterio nuevo con un id libre (c1, c2, …) y dos niveles vacíos. */
export function nuevoCriterio(existentes: CriterioEditor[]): CriterioEditor {
  const ids = new Set(existentes.map((c) => c.id.trim().toLowerCase()));
  let numero = existentes.length + 1;
  while (ids.has(`c${numero}`)) numero += 1;
  return {
    clave: nuevaClave(),
    id: `c${numero}`,
    competencia: "",
    nombre: "",
    ponderacion: null,
    niveles: [nuevoNivel(), nuevoNivel()],
  };
}

export function rubricaVacia(tituloLaboratorio: string): RubricaEditor {
  return { titulo: `Rúbrica – ${tituloLaboratorio}`, criterios: [] };
}

export function rubricaAEditor(rubrica: Rubrica): RubricaEditor {
  return {
    titulo: rubrica.titulo,
    criterios: rubrica.criterios.map((criterio) => ({
      ...criterio,
      clave: nuevaClave(),
      niveles: criterio.niveles.map((nivel) => ({ ...nivel, clave: nuevaClave() })),
    })),
  };
}

/** Convierte al contrato. Solo se usa cuando no hay números vacíos (ver `tieneNumerosVacios`). */
export function editorARubrica(editor: RubricaEditor): Rubrica {
  return {
    titulo: editor.titulo.trim(),
    criterios: editor.criterios.map((c) => ({
      id: c.id.trim(),
      competencia: c.competencia.trim(),
      nombre: c.nombre.trim(),
      ponderacion: c.ponderacion ?? 0,
      niveles: c.niveles.map((n) => ({ nombre: n.nombre.trim(), puntaje: n.puntaje ?? 0, descriptor: n.descriptor.trim() })),
    })),
  };
}

export function tieneNumerosVacios(editor: RubricaEditor): boolean {
  return editor.criterios.some((c) => c.ponderacion === null || c.niveles.some((n) => n.puntaje === null));
}

export function tieneContenido(editor: RubricaEditor): boolean {
  return editor.criterios.length > 0;
}

/** Mueve un elemento `desplazamiento` posiciones; si sale de los límites devuelve la lista igual. */
export function mover<T>(lista: T[], indice: number, desplazamiento: number): T[] {
  const destino = indice + desplazamiento;
  if (destino < 0 || destino >= lista.length) return lista;
  const copia = [...lista];
  const [elemento] = copia.splice(indice, 1);
  copia.splice(destino, 0, elemento);
  return copia;
}

export function reemplazar<T>(lista: T[], indice: number, valor: T): T[] {
  return lista.map((actual, i) => (i === indice ? valor : actual));
}

export function quitar<T>(lista: T[], indice: number): T[] {
  return lista.filter((_, i) => i !== indice);
}

/** "" o texto no numérico → null (campo vacío). */
export function parsearNumero(texto: string): number | null {
  if (texto.trim() === "") return null;
  const valor = Number(texto.replace(",", "."));
  return Number.isFinite(valor) ? valor : null;
}
