import type { Metadata } from "next";
import Link from "next/link";
import { TarjetaIntegrante, type Integrante } from "@/components/tarjeta-integrante";

export const metadata: Metadata = {
  title: "Equipo",
  description: "Integrantes del proyecto Asesor Pedagógico Inteligente y su rol.",
};

const URL_USO_IA = "https://github.com/lunamm25/Proyecto-final-IA/blob/main/docs/USO_IA.md";

const integrantes: Integrante[] = [
  {
    nombre: "Laura Valentina Suarez",
    rol: "Rol 1 – IA y motor de evaluación",
    foto: "/equipo/laura.jpg",
    iniciales: "LS",
  },
  {
    nombre: "Mariana Otalvaro Gutierrez",
    rol: "Rol 2 – Backend y lógica de negocio",
    foto: "/equipo/mariana.jpg",
    iniciales: "MO",
  },
  {
    nombre: "Daniela Garcia Valencia",
    rol: "Rol 3 – Frontend y experiencia interactiva",
    foto: "/equipo/daniela.jpg",
    iniciales: "DG",
  },
  {
    nombre: "Luna Murillo Moreno",
    rol: "Rol 4 – DevOps, verificación y calidad",
    foto: "/equipo/luna.jpg",
    iniciales: "LM",
  },
];

export default function Equipo() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:py-16">
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Nuestro equipo</h1>
      <p className="mt-3 max-w-2xl text-muted-foreground">
        Cuatro integrantes, cada una responsable de un rol del proyecto Asesor Pedagógico Inteligente.
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {integrantes.map((integrante) => (
          <TarjetaIntegrante key={integrante.nombre} integrante={integrante} />
        ))}
      </div>

      <section aria-labelledby="titulo-uso-ia" className="mt-16 rounded-xl border bg-muted/40 p-6 sm:p-8">
        <h2 id="titulo-uso-ia" className="text-2xl font-semibold tracking-tight">
          Cómo usamos IA para construir esto
        </h2>
        <p className="mt-3 max-w-3xl text-muted-foreground">
          Cada integrante trabajó su rol con asistentes de IA y verificó cada cambio con pruebas
          automáticas y revisión manual. El detalle de herramientas, actividades por fase, decisiones y
          limitaciones está en{" "}
          <a
            href={URL_USO_IA}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-foreground underline underline-offset-4"
          >
            docs/USO_IA.md
          </a>
          .
        </p>
        <Link href="/" className="mt-4 inline-block text-sm font-medium underline underline-offset-4">
          Volver al inicio
        </Link>
      </section>
    </div>
  );
}
