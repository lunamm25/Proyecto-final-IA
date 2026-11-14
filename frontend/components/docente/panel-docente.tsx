"use client";

import Link from "next/link";
import { Bot, ClipboardCheck, FlaskConical, ListChecks, Users, type LucideIcon } from "lucide-react";
import { useSesion } from "@/components/proveedor-sesion";
import type { Rol } from "@/lib/tipos";

interface TarjetaPanel {
  href: string;
  titulo: string;
  descripcion: string;
  Icono: LucideIcon;
  roles: Rol[];
}

const TARJETAS: TarjetaPanel[] = [
  {
    href: "/docente/laboratorios",
    titulo: "Laboratorios",
    descripcion: "Crea y edita los laboratorios de cada cohorte.",
    Icono: FlaskConical,
    roles: ["docente", "admin"],
  },
  {
    href: "/docente/laboratorios",
    titulo: "Rúbricas",
    descripcion: "La rúbrica se carga y edita desde cada laboratorio: abre Laboratorios y usa el botón «Rúbrica».",
    Icono: ListChecks,
    roles: ["docente", "admin"],
  },
  {
    href: "/docente/revision",
    titulo: "Revisión de evaluaciones",
    descripcion: "Revisa lo que propuso la IA, ajusta niveles con motivo, aprueba y publica.",
    Icono: ClipboardCheck,
    roles: ["docente", "admin"],
  },
  {
    href: "/docente/config-ia",
    titulo: "Configuración de IA",
    descripcion: "Elige el proveedor, el modelo y la temperatura, y prueba la conexión.",
    Icono: Bot,
    roles: ["docente", "admin"],
  },
  {
    href: "/admin/usuarios",
    titulo: "Usuarios",
    descripcion: "Consulta los usuarios registrados y cambia su rol.",
    Icono: Users,
    roles: ["admin"],
  },
];

function Tarjeta({ tarjeta }: { tarjeta: TarjetaPanel }) {
  const { Icono } = tarjeta;
  return (
    <li>
      <Link
        href={tarjeta.href}
        className="flex h-full gap-4 rounded-xl border bg-card p-5 outline-none transition-colors hover:bg-muted/40 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icono className="size-5" aria-hidden="true" />
        </span>
        <span>
          <span className="block font-semibold">{tarjeta.titulo}</span>
          <span className="mt-1 block text-sm text-muted-foreground">{tarjeta.descripcion}</span>
        </span>
      </Link>
    </li>
  );
}

/** Panel de inicio del docente/admin: accesos directos a cada sección. */
export function PanelDocente() {
  const { perfil } = useSesion();
  if (!perfil) return null;
  const visibles = TARJETAS.filter((tarjeta) => tarjeta.roles.includes(perfil.rol));
  return (
    <>
      <h1 className="text-3xl font-bold tracking-tight">{perfil.nombre?.trim() ? `Hola, ${perfil.nombre.trim()}` : "Hola"}</h1>
      <p className="mt-2 text-muted-foreground">
        Desde aquí gestionas laboratorios, rúbricas, evaluaciones y la configuración de IA.
      </p>
      <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Secciones del panel">
        {visibles.map((tarjeta) => (
          <Tarjeta key={tarjeta.titulo} tarjeta={tarjeta} />
        ))}
      </ul>
    </>
  );
}
