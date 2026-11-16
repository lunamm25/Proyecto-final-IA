// En la interfaz se dice "corte". El backend (y la base de datos) siguen llamando "cohorte" a la entidad
// y envían nombres como "Cohorte 1": este ayudante solo cambia el texto que se muestra.

/** Cambia "Cohorte"/"cohorte(s)" por "Corte"/"corte(s)" en un texto que viene del backend. */
export function textoCorte(texto: string): string {
  return texto.replace(/\b([Cc])ohorte(s?)\b/g, (_, inicial: string, plural: string) => `${inicial}orte${plural}`);
}
