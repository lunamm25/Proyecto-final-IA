import Link from "next/link";
import {
  BrainCircuit,
  ClipboardCheck,
  FileText,
  FolderOpen,
  Network,
  Settings2,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const URL_USO_IA = "https://github.com/lunamm25/Proyecto-final-IA/blob/main/docs/USO_IA.md";

const objetivos = [
  "Evaluar las evidencias de los laboratorios de las cohortes 1 y 2 criterio por criterio, citando evidencias concretas.",
  "Calcular la nota (0,0–5,0) de forma determinista en el backend con las ponderaciones de la rúbrica.",
  "Mantener al docente en el centro: revisa, ajusta con justificación, aprueba y publica cada evaluación.",
  "Consolidar el aprendizaje del estudiante en un informe integral y un mapa mental de competencias en IA.",
];

const funcionalidades = [
  { icono: FolderOpen, titulo: "Portafolio académico", texto: "Entrega por laboratorio: informe PDF, código (ZIP o GitHub) e imágenes opcionales." },
  { icono: ClipboardCheck, titulo: "Gestión de rúbricas", texto: "Carga, extracción con IA, validación automática, edición y versionado." },
  { icono: BrainCircuit, titulo: "Evaluación inteligente", texto: "Nivel propuesto por criterio con evidencias citadas, fortalezas y recomendaciones." },
  { icono: ShieldCheck, titulo: "Verificación de código", texto: "Análisis estático y pruebas en un entorno aislado (sandbox)." },
  { icono: UserCheck, titulo: "Revisión docente", texto: "Human-in-the-Loop: ajustes con motivo, historial y publicación controlada." },
  { icono: FileText, titulo: "Informe integral", texto: "Evolución entre cohortes, dominio por competencia, brechas y plan de fortalecimiento." },
  { icono: Network, titulo: "Mapa mental interactivo", texto: "Competencias coloreadas por dominio, exploración y descarga en PNG o JSON." },
  { icono: Settings2, titulo: "IA configurable", texto: "Proveedor en la nube (Gemini) o local/compatible con OpenAI (Ollama, Groq, OpenRouter)." },
];

const tecnologias = [
  { capa: "Frontend", detalle: "Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, React Flow y Recharts" },
  { capa: "Backend", detalle: "Python 3.11, FastAPI, Pydantic v2 y SQLAlchemy 2" },
  { capa: "Datos", detalle: "Supabase: Postgres, autenticación y almacenamiento privado" },
  { capa: "IA", detalle: "Capa LLMProvider con Gemini y proveedores compatibles con OpenAI" },
  { capa: "Verificación", detalle: "ast, ruff y radon (estático) · pytest en sandbox" },
  { capa: "Despliegue", detalle: "Vercel (frontend) y Render (backend)" },
];

const aportes = [
  "Evaluaciones consistentes: misma rúbrica, mismos criterios y temperatura baja del modelo.",
  "Explicables: cada nivel propuesto se sustenta con evidencias verificables del trabajo entregado.",
  "Trazables: se guarda proveedor, modelo, versión del prompt, versión de la rúbrica y cada ajuste.",
  "Validadas por el docente: el estudiante solo ve evaluaciones publicadas tras la revisión humana.",
];

export default function Inicio() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:py-16">
      <section className="flex flex-col items-start gap-6">
        <p className="rounded-full border px-3 py-1 text-xs font-medium text-muted-foreground">
          Proyecto final · Profundización I – IA · Universidad de Manizales
        </p>
        <h1 className="max-w-3xl text-3xl font-bold tracking-tight sm:text-5xl">
          Asesor Pedagógico Inteligente
        </h1>
        <p className="max-w-3xl text-lg leading-relaxed text-muted-foreground">
          Plataforma web en la que el estudiante sube las evidencias de sus laboratorios junto con la
          descripción y la rúbrica de cada uno. La IA analiza las evidencias criterio por criterio, cita
          evidencias concretas y propone un nivel de desempeño; el backend calcula la nota con las
          ponderaciones de la rúbrica y el docente revisa, ajusta y aprueba antes de publicar.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg" className="h-10 px-4">
            <Link href="/login">Iniciar sesión</Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="h-10 px-4">
            <Link href="/equipo">Conoce al equipo</Link>
          </Button>
        </div>
      </section>

      <section aria-labelledby="titulo-objetivos" className="mt-16">
        <h2 id="titulo-objetivos" className="text-2xl font-semibold tracking-tight">Objetivos</h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {objetivos.map((objetivo) => (
            <li key={objetivo} className="rounded-lg border bg-card p-4 text-sm leading-relaxed">
              {objetivo}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="titulo-funcionalidades" className="mt-16">
        <h2 id="titulo-funcionalidades" className="text-2xl font-semibold tracking-tight">Funcionalidades</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {funcionalidades.map(({ icono: Icono, titulo, texto }) => (
            <article key={titulo} className="rounded-lg border bg-card p-4">
              <Icono className="size-5 text-primary" aria-hidden="true" />
              <h3 className="mt-3 font-medium">{titulo}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{texto}</p>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="titulo-tecnologias" className="mt-16">
        <h2 id="titulo-tecnologias" className="text-2xl font-semibold tracking-tight">Tecnologías</h2>
        <dl className="mt-4 divide-y rounded-lg border bg-card">
          {tecnologias.map((tecnologia) => (
            <div key={tecnologia.capa} className="grid gap-1 p-4 sm:grid-cols-[10rem_1fr]">
              <dt className="font-medium">{tecnologia.capa}</dt>
              <dd className="text-sm text-muted-foreground">{tecnologia.detalle}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="titulo-aportes" className="mt-16">
        <h2 id="titulo-aportes" className="text-2xl font-semibold tracking-tight">Aportes</h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {aportes.map((aporte) => (
            <li key={aporte} className="rounded-lg border bg-card p-4 text-sm leading-relaxed">
              {aporte}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="titulo-uso-ia" className="mt-16 rounded-xl border bg-muted/40 p-6 sm:p-8">
        <h2 id="titulo-uso-ia" className="text-2xl font-semibold tracking-tight">
          Cómo usamos IA para construir esto
        </h2>
        <p className="mt-3 max-w-3xl text-muted-foreground">
          Usamos asistentes de IA a lo largo del ciclo de vida del software: requisitos, diseño,
          implementación, pruebas y documentación, siempre con verificación humana de cada cambio.
          Documentamos las herramientas, decisiones, problemas, limitaciones y costos.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Button asChild variant="outline" className="h-9 px-3">
            <a href={URL_USO_IA} target="_blank" rel="noopener noreferrer">
              Leer docs/USO_IA.md en GitHub
            </a>
          </Button>
          <Button asChild variant="link" className="h-9 px-0">
            <Link href="/equipo">Ver el equipo</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
