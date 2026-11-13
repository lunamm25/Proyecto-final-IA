# Guía de arranque — Asesor Pedagógico Inteligente

Este kit sigue la metodología recomendada: **un documento maestro `.md` con todo el contexto → reglas en `CLAUDE.md` → un agente por rol más revisores de calidad y seguridad → `/init` en Claude Code → implementar por partes, verificando cada cambio.**

## Qué hay en el kit
```
LEEME_PRIMERO.md            ← esta guía (prompts listos para copiar)
CLAUDE.md                   ← reglas permanentes: verificar cada cambio, metodología, tokens, qué no hacer
docs/REQUISITOS.md          ← documento maestro: RF, RNF, casos de uso, esquemas, API, BD, plan por día
docs/USO_IA.md              ← plantilla obligatoria: herramientas de IA usadas, aportes, limitaciones
docs/PROGRESO.md            ← bitácora: qué está hecho y dónde quedó cada una
.claude/agents/             ← motor-ia (Rol 1), backend (Rol 2), frontend (Rol 3), devops-calidad (Rol 4),
                              revisor-calidad, revisor-seguridad
.claude/commands/verificar.md ← comando /verificar
```

---

## Paso 0 — Antes de empezar (Luna o quien tenga más tiempo hoy, ~30 min)
1. Crear un repositorio en GitHub, p. ej. `asesor-pedagogico`, e invitar a las 4.
2. Copiar **todo** el contenido de este kit en la raíz del repo (incluida la carpeta oculta `.claude`) y hacer commit.
3. Crear cuentas gratis en **Supabase**, **Vercel**, **Render** y una **API key de Gemini** (Google AI Studio). Guardar las claves en un lugar privado; **nunca** en el repo.
4. Completar en `docs/REQUISITOS.md` §5 RF-11 los apellidos de cada integrante.

## Paso 1 — Abrir Claude Code e iniciar (cada integrante, en su computador)
```bash
git clone https://github.com/<usuario>/asesor-pedagogico.git
cd asesor-pedagogico
git checkout -b rol1-ia              # Laura: rol1-ia · Mariana: rol2-backend · Daniela: rol3-frontend · Luna: rol4-devops
claude
```
Dentro de Claude Code, escribe `/init` y luego pega:

> Ya existe un `CLAUDE.md` con reglas del equipo y el documento maestro `docs/REQUISITOS.md`. Léelos completos. No reemplaces las reglas existentes: si `/init` propone cambios a CLAUDE.md, solo agrega lo que falte. Después confírmame en 5 líneas que entendiste: el objetivo, el stack, la regla de verificación, la regla de la nota y cuál es mi rol (Rol X). No escribas código todavía.

## Paso 2 — Arranque del proyecto (UNA sola persona, en `main`: Luna, Rol 4)
> Usa el agente devops-calidad. Crea la estructura del repositorio según CLAUDE.md §2: proyecto Next.js en `frontend/` (TypeScript, Tailwind, App Router, ESLint, shadcn/ui inicializado) y proyecto FastAPI mínimo en `backend/` con `/api/salud`, `requirements.txt`, ruff y pytest con un test de salud. Agrega `.gitignore`, `.env.example` en ambos y el workflow de CI. Explícame cada comando que debo correr. Al final ejecuta /verificar.

Cuando pase, se hace push a `main` y cada una hace `git pull` en su rama (`git merge main`).

## Paso 3 — Prompts por rol (cada una en su sesión, con su cuenta)

Usa siempre el mismo patrón: **una tarea pequeña por prompt**, y al final pide `/verificar`.

### Rol 1 — IA y motor de evaluación (Laura)
1. > Usa el agente motor-ia. Tarea: `schemas.py` y `providers.py` (Gemini + OpenAI-compatible) con `FakeProvider` para tests y un script `probar_proveedor.py`. Verifica.
2. > Usa el agente motor-ia. Tarea: prompt y función de extracción de rúbricas a `RubricaSchema` (RF-03 CA1). Pruébalo con una rúbrica real del curso. Verifica.
3. > Usa el agente motor-ia. Tarea: `evaluador.py` con reintentos de validación y `citas.py` (RF-05). Verifica.
4. > Usa el agente motor-ia. Tarea: mapeo a temáticas y narrativa del informe (RF-08 CA3, RF-09 CA2). Verifica.

### Rol 2 — Backend y lógica (Mariana)
1. > Usa el agente backend. Tarea: configuración, conexión a Supabase Postgres, modelos y migración SQL de §10, y `seed.py` con cohortes 1 y 2. Verifica.
2. > Usa el agente backend. Tarea: autenticación con JWT de Supabase y permisos por rol, con tests. Verifica.
3. > Usa el agente backend. Tarea: `services/nota.py` con TODOS los tests de §8 escritos primero. Verifica.
4. > Usa el agente backend. Tarea: laboratorios, rúbricas (validador de inconsistencias + versiones) y entregas con Storage (RF-02, RF-03, RF-04). Verifica.
5. > Usa el agente backend. Tarea: flujo de evaluación con BackgroundTasks, estados, ajustes con auditoría y traza (RF-05, RF-07), usando el evaluador del Rol 1. Verifica.
6. > Usa el agente backend. Tarea: endpoints de informe y mapa (RF-08, RF-09). Verifica.

### Rol 3 — Frontend y experiencia (Daniela)
1. > Usa el agente frontend. Tarea: layout general (barra de navegación según rol, pie de página), página `/` con el abstract del proyecto y página `/equipo` con tarjetas de foto, nombre y rol (fotos en `public/equipo/`). Diseño profesional y limpio. Verifica al terminar.
2. > Usa el agente frontend. Tarea: login y registro con Supabase Auth, cliente `lib/api.ts` que envía el JWT, tipos en `lib/tipos.ts` según el contrato §11 y protección de rutas por rol. Usa mocks en `lib/mocks.ts` mientras el backend no esté listo. Verifica.
3. > Usa el agente frontend. Tarea: portafolio y pantalla de entrega (RF-04). Verifica.
4. > Usa el agente frontend. Tarea: editor de rúbricas con inconsistencias en vivo (RF-03 CA3). Verifica.
5. > Usa el agente frontend. Tarea: vista de evaluación con progreso y revisión docente con ajuste por criterio (RF-05, RF-07). Verifica.
6. > Usa el agente frontend. Tarea: informe integral con gráficas y descarga PDF (RF-08). Verifica.
7. > Usa el agente frontend. Tarea: mapa mental interactivo con React Flow (RF-09). Verifica.
8. > Reemplaza los mocks por el API real (URL en `NEXT_PUBLIC_API_URL`) y prueba cada pantalla contra el backend desplegado.

### Rol 4 — DevOps, verificación y calidad (Luna)
1. (Paso 2 de arriba)
2. > Usa el agente devops-calidad. Tarea: extracción segura de ZIP/GitHub y verificador estático (RF-06 CA1) con tests. Verifica.
3. > Usa el agente devops-calidad. Tarea: sandbox según §9 con tests de timeout y entorno limpio. Verifica.
4. > Usa el agente devops-calidad. Tarea: despliegue (Supabase, Render, Vercel), variables de entorno y verificación de la URL pública.
5. > Usa el agente devops-calidad. Tarea: datos y cuentas de demo + `docs/CHECKLIST_ENTREGA.md`.

## Paso 4 — Antes de cada PR a `main`
> Usa el agente revisor-calidad para revisar mi rama contra `main`.

y, si tocaste login, permisos, archivos, sandbox o despliegue:
> Usa el agente revisor-seguridad para revisar mi rama contra `main`.

Corrige lo 🔴, vuelve a correr `/verificar` y abre el PR.

---

## Consejos para no quedarse sin tokens
- **Cada una trabaja con su propia cuenta de Claude** y solo en su rol: así el límite de 5 horas se reparte entre 4.
- Prompts cortos y concretos; no pidas "haz todo el backend".
- Si la conversación se alarga mucho, usa `/compact` o abre una sesión nueva (el contexto vive en CLAUDE.md, REQUISITOS.md y PROGRESO.md).
- Antes de cerrar: *"Actualiza docs/PROGRESO.md con lo que hicimos y el siguiente paso."*
- Para preguntas generales (explicaciones, dudas de conceptos), usa el chat normal y no Claude Code.
- Ve anotando en `docs/USO_IA.md` cada vez que la IA te ayudó o se equivocó: es obligatorio en la entrega y sirve para la socialización.

## Orden si se acaba el tiempo
Login → laboratorios/rúbricas → portafolio → evaluación + revisión docente → página del equipo → informe → mapa mental → tests en sandbox → panel de configuración de IA.
