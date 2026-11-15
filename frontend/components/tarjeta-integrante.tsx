"use client";

import Image from "next/image";
import { useState } from "react";

export interface Integrante {
  nombre: string;
  rol: string;
  foto: string;
  iniciales: string;
}

export function TarjetaIntegrante({ integrante }: { integrante: Integrante }) {
  const [fotoFallida, setFotoFallida] = useState(false);

  return (
    <article className="flex flex-col items-center rounded-xl border bg-card p-6 text-center">
      <div className="relative size-32 overflow-hidden rounded-full bg-muted">
        {fotoFallida ? (
          <div
            role="img"
            aria-label={`Iniciales de ${integrante.nombre}`}
            className="flex size-full items-center justify-center bg-primary text-3xl font-semibold text-primary-foreground"
          >
            {integrante.iniciales}
          </div>
        ) : (
          <Image
            src={integrante.foto}
            alt={`Foto de ${integrante.nombre}`}
            fill
            sizes="128px"
            className="object-cover"
            onError={() => setFotoFallida(true)}
          />
        )}
      </div>
      <h2 className="mt-4 text-lg font-semibold">{integrante.nombre}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{integrante.rol}</p>
    </article>
  );
}
