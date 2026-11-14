"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { GraduationCap, LogOut, Menu, X } from "lucide-react";
import { AvatarPerfil } from "@/components/avatar-perfil";
import { useSesion } from "@/components/proveedor-sesion";
import { nombreVisible } from "@/lib/perfil";
import { cn } from "@/lib/utils";
import type { Rol } from "@/lib/tipos";

interface EnlaceNav {
  href: string;
  etiqueta: string;
}

function enlacesPorRol(rol: Rol | null): EnlaceNav[] {
  if (rol === "estudiante") {
    return [
      { href: "/portafolio", etiqueta: "Portafolio" },
      { href: "/informe", etiqueta: "Informe" },
      { href: "/mapa", etiqueta: "Mapa mental" },
    ];
  }
  if (rol === "docente" || rol === "admin") {
    const enlaces: EnlaceNav[] = [
      { href: "/docente", etiqueta: "Panel" },
      { href: "/docente/laboratorios", etiqueta: "Laboratorios y rúbricas" },
      { href: "/docente/revision", etiqueta: "Evaluaciones" },
      { href: "/docente/config-ia", etiqueta: "Configuración IA" },
    ];
    if (rol === "admin") enlaces.push({ href: "/admin/usuarios", etiqueta: "Usuarios" });
    return enlaces;
  }
  return [
    { href: "/", etiqueta: "Inicio" },
    { href: "/equipo", etiqueta: "Equipo" },
    { href: "/login", etiqueta: "Iniciar sesión" },
  ];
}

function estaActivo(pathname: string, href: string): boolean {
  if (href === "/" || href === "/docente") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Navegacion() {
  const pathname = usePathname();
  const router = useRouter();
  const [abierto, setAbierto] = useState(false);
  const { estado, perfil, cerrarSesion } = useSesion();
  const enlaces = estado === "cargando" ? [] : enlacesPorRol(perfil?.rol ?? null);
  const conSesion = estado === "autenticado" || estado === "error";

  const salir = async () => {
    setAbierto(false);
    await cerrarSesion();
    router.push("/login");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur print:hidden">
      <nav
        aria-label="Navegación principal"
        className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4"
      >
        <Link href="/" className="flex items-center gap-2 font-semibold" onClick={() => setAbierto(false)}>
          <GraduationCap className="size-5 text-primary" aria-hidden="true" />
          <span>Asesor Pedagógico Inteligente</span>
        </Link>

        <ul className="hidden items-center gap-1 md:flex">
          {enlaces.map((enlace) => (
            <li key={enlace.href}>
              <Link
                href={enlace.href}
                aria-current={estaActivo(pathname, enlace.href) ? "page" : undefined}
                className={cn(
                  "rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  estaActivo(pathname, enlace.href) && "bg-muted font-medium text-foreground",
                )}
              >
                {enlace.etiqueta}
              </Link>
            </li>
          ))}
          {perfil && (
            <li className="ml-2 flex items-center gap-2" title={`${nombreVisible(perfil.nombre, "Usuario")} (${perfil.rol})`}>
              <AvatarPerfil perfil={perfil} />
              <span className="sr-only">
                Sesión de {nombreVisible(perfil.nombre, "usuario sin nombre")}, rol {perfil.rol}
              </span>
            </li>
          )}
          {conSesion && (
            <li>
              <button
                type="button"
                onClick={salir}
                className="ml-2 inline-flex items-center gap-1 rounded-md border px-3 py-2 text-sm hover:bg-muted"
              >
                <LogOut className="size-4" aria-hidden="true" />
                Cerrar sesión
              </button>
            </li>
          )}
        </ul>

        <button
          type="button"
          className="inline-flex size-9 items-center justify-center rounded-md hover:bg-muted md:hidden"
          aria-label={abierto ? "Cerrar menú" : "Abrir menú"}
          aria-expanded={abierto}
          aria-controls="menu-movil"
          onClick={() => setAbierto((valor) => !valor)}
        >
          {abierto ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </nav>

      {abierto && (
        <ul id="menu-movil" className="border-t px-4 py-2 md:hidden">
          {perfil && (
            <li className="flex items-center gap-3 px-3 py-2">
              <AvatarPerfil perfil={perfil} />
              <span className="text-sm">
                <span className="font-medium">{nombreVisible(perfil.nombre, "Usuario")}</span>
                <span className="text-muted-foreground"> · {perfil.rol}</span>
              </span>
            </li>
          )}
          {enlaces.map((enlace) => (
            <li key={enlace.href}>
              <Link
                href={enlace.href}
                onClick={() => setAbierto(false)}
                aria-current={estaActivo(pathname, enlace.href) ? "page" : undefined}
                className={cn(
                  "block rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground",
                  estaActivo(pathname, enlace.href) && "bg-muted font-medium text-foreground",
                )}
              >
                {enlace.etiqueta}
              </Link>
            </li>
          ))}
          {conSesion && (
            <li>
              <button
                type="button"
                onClick={salir}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <LogOut className="size-4" aria-hidden="true" />
                Cerrar sesión
              </button>
            </li>
          )}
        </ul>
      )}
    </header>
  );
}
