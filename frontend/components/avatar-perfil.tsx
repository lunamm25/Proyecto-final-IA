"use client";

import Image from "next/image";
import { useState } from "react";
import { iniciales, nombreVisible } from "@/lib/perfil";
import { cn } from "@/lib/utils";
import type { Perfil } from "@/lib/tipos";

interface AvatarPerfilProps {
  perfil: Pick<Perfil, "nombre" | "foto_url">;
  tamano?: number;
  className?: string;
}

/** Foto del perfil si el backend la envía; si no hay o no carga, las iniciales del nombre. */
export function AvatarPerfil({ perfil, tamano = 32, className }: AvatarPerfilProps) {
  const [fotoFallida, setFotoFallida] = useState<string | null>(null);
  const foto = perfil.foto_url?.trim() || null;
  const mostrarFoto = foto !== null && fotoFallida !== foto;
  const nombre = nombreVisible(perfil.nombre, "Usuario");

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border bg-muted text-xs font-semibold text-muted-foreground",
        className,
      )}
      style={{ width: tamano, height: tamano }}
    >
      {mostrarFoto ? (
        <Image
          src={foto}
          alt={`Foto de ${nombre}`}
          width={tamano}
          height={tamano}
          unoptimized
          className="size-full object-cover"
          onError={() => setFotoFallida(foto)}
        />
      ) : (
        <span aria-hidden="true">{iniciales(perfil.nombre)}</span>
      )}
    </span>
  );
}
