import type { Perfil, Rol, Usuario } from "@/lib/tipos";

export const ROLES: Rol[] = ["estudiante", "docente", "admin"];

export const TEXTO_ROL: Record<Rol, string> = {
  estudiante: "Estudiante",
  docente: "Docente",
  admin: "Administrador",
};

export type FiltroRol = Rol | "todos";

export function esFiltroRol(valor: string): valor is FiltroRol {
  return valor === "todos" || ROLES.some((rol) => rol === valor);
}

export function esRol(valor: string): valor is Rol {
  return ROLES.some((rol) => rol === valor);
}

function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

/** Filtra en el cliente la lista recibida del backend (no calcula nada nuevo). */
export function filtrarUsuarios(usuarios: Usuario[], busqueda: string, filtro: FiltroRol): Usuario[] {
  const termino = normalizar(busqueda);
  return usuarios.filter((usuario) => {
    if (filtro !== "todos" && usuario.rol !== filtro) return false;
    if (termino === "") return true;
    return normalizar(usuario.nombre ?? "").includes(termino) || normalizar(usuario.correo ?? "").includes(termino);
  });
}

/** Máximo del motivo opcional (CambioRolEntrada del backend). */
export const MAX_MOTIVO_ROL = 500;

/**
 * Motivo por el que no se ofrece cambiar el rol (solo UX; el backend decide y responde 409 con el detalle).
 * La gestión es solo de admin, y el backend no deja que un admin se quite su propio rol de administrador.
 * El caso "sería el último administrador" lo resuelve el backend (409) y se muestra su mensaje tal cual.
 */
export function motivoBloqueo(usuario: Usuario, actual: Perfil): string | null {
  if (usuario.id === actual.id && usuario.rol === "admin") {
    return "No puedes quitarte tu propio rol de administrador. Pide a otro administrador que lo haga.";
  }
  return null;
}
