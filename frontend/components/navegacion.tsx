"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { GraduationCap, Menu, X } from "lucide-react";
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
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

interface NavegacionProps {
  rol: Rol | null;
}

export function Navegacion({ rol }: NavegacionProps) {
  const pathname = usePathname();
  const [abierto, setAbierto] = useState(false);
  const enlaces = enlacesPorRol(rol);

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
        </ul>
      )}
    </header>
  );
}
