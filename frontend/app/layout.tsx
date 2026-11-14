import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Navegacion } from "@/components/navegacion";
import { PiePagina } from "@/components/pie-pagina";
import { ProveedorSesion } from "@/components/proveedor-sesion";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Asesor Pedagógico Inteligente",
    template: "%s · Asesor Pedagógico Inteligente",
  },
  description:
    "Plataforma que evalúa con IA las evidencias de laboratorio por criterio de rúbrica, con revisión docente, informe integral y mapa mental de competencias.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <ProveedorSesion>
          <Navegacion />
          <main className="flex flex-1 flex-col">{children}</main>
        </ProveedorSesion>
        <PiePagina />
      </body>
    </html>
  );
}
