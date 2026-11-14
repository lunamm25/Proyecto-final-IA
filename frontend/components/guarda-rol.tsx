"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Cargando, MensajeError } from "@/components/estados";
import { useSesion } from "@/components/proveedor-sesion";
import type { Rol } from "@/lib/tipos";

interface GuardaRolProps {
  roles: Rol[];
  children: React.ReactNode;
}

/** Muestra el contenido solo si el rol del usuario está permitido. Es UX: el backend aplica la seguridad real. */
export function GuardaRol({ roles, children }: GuardaRolProps) {
  const { estado, perfil, error, recargar } = useSesion();
  const pathname = usePathname();

  if (estado === "cargando") return <Cargando texto="Verificando tu sesión…" />;

  if (estado === "error") {
    return <MensajeError mensaje={error ?? "No se pudo cargar tu perfil."} alReintentar={() => void recargar()} />;
  }

  if (estado === "anonimo" || !perfil) {
    return (
      <MensajeError titulo="Debes iniciar sesión" mensaje="Ingresa con tu cuenta para ver esta página.">
        <Link
          href={`/login?siguiente=${encodeURIComponent(pathname)}`}
          className="mt-4 inline-block text-sm font-medium underline underline-offset-4"
        >
          Ir a iniciar sesión
        </Link>
      </MensajeError>
    );
  }

  if (!roles.includes(perfil.rol)) {
    return (
      <MensajeError
        titulo="No tienes permiso para ver esta página"
        mensaje={`Error 403: esta sección no está disponible para el rol ${perfil.rol}.`}
      >
        <Link href="/" className="mt-4 inline-block text-sm font-medium underline underline-offset-4">
          Volver al inicio
        </Link>
      </MensajeError>
    );
  }

  return <>{children}</>;
}
