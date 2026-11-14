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

/**
 * Motivo por el que el usuario actual no puede cambiar el rol de `usuario` (solo UX; el backend decide).
 * - Nadie se cambia su propio rol: así no se quita por error el acceso de docente/admin.
 * - Solo un admin modifica a otro admin.
 */
export function motivoBloqueo(usuario: Usuario, actual: Perfil): string | null {
  if (usuario.id === actual.id) {
    return "No puedes cambiar tu propio rol: perderías el acceso a esta gestión. Pídeselo a otro administrador.";
  }
  if (usuario.rol === "admin" && actual.rol !== "admin") {
    return "Solo un administrador puede cambiar el rol de otro administrador.";
  }
  return null;
}

/** El contrato no dice quién asigna "admin": por precaución solo lo ofrece a un admin. */
export function puedeAsignar(rol: Rol, actual: Perfil): boolean {
  return rol !== "admin" || actual.rol === "admin";
}
