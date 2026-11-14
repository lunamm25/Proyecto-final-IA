# Progreso del proyecto

| RF | Descripción | Responsable | Estado | Verificado por / fecha |
|---|---|---|---|---|
| RF-01 | Autenticación y usuarios | Rol 2 + Rol 3 | Pendiente | |
| RF-02 | Cohortes y laboratorios | Rol 2 | Frontend hecho (mocks): /docente/laboratorios · falta backend | Daniela (Rol 3) · 2026-11-13 |
| RF-03 | Gestión de rúbricas | Rol 1 + 2 + 3 | Frontend hecho (mocks): editor /docente/rubricas/[labId] con inconsistencias en vivo (CA3) · falta backend | Daniela (Rol 3) · 2026-11-13 |
| RF-04 | Portafolio académico | Rol 2 + 3 | Frontend hecho (mocks): /portafolio y /portafolio/[labId]/entregar · falta backend | Daniela (Rol 3) · 2026-11-13 |
| RF-05 | Evaluación inteligente | Rol 1 + 2 + 3 | Pendiente | |
| RF-06 | Verificación de código / sandbox | Rol 4 | Pendiente | |
| RF-07 | Revisión docente (HITL) | Rol 2 + 3 | Pendiente | |
| RF-08 | Informe integral | Rol 1 + 2 + 3 | Pendiente | |
| RF-09 | Mapa mental | Rol 1 + 2 + 3 | Pendiente | |
| RF-10 | Configuración de IA | Rol 1 + 3 | Pendiente | |
| RF-11 | Proyecto y equipo | Rol 3 | Hecho | Daniela (Rol 3) · 2026-11-13 |
| Deploy | URL pública + datos demo | Rol 4 | Pendiente | |

## Bitácora de sesiones
<!-- Formato: fecha · integrante · qué se hizo · siguiente paso -->
- 2026-11-13 · Laura (Rol 1) · base del motor IA: schemas, providers, tests · siguiente paso: prueba real con Gemini y prompts versionados
- 2026-11-13 · Laura (Rol 1) · RF-03 CA1: extracción de rúbricas con IA (prompt extraer_rubrica v1.0, rubricas.py, lectura .md/.docx/.pdf, probado con 3 rúbricas reales en Gemini) · siguiente paso: afinar descriptores de niveles generados (idea: que el LLM extraiga elementos literales y el código arme la plantilla); validador RF-03 CA2 · pendientes: el modelo no respeta siempre los puntajes 5.0/3.5/0.0 de niveles generados (en LAB01 salieron 10/5/0): asignarlos en código; el título de Manizales pierde el subtítulo; descriptores generados pueden traer adjetivos no presentes en el documento
- 2026-11-13 · Daniela (Rol 3) · RF-11: layout (navegación por rol, pie de página), página / con abstract, /equipo con tarjetas; cliente Supabase perezoso; dependencias supabase-js, @xyflow/react, recharts, html-to-image · lint, tsc y build OK · siguiente paso: subir fotos a frontend/public/equipo/ y login con Supabase (RF-01)
- 2026-11-13 · Daniela (Rol 3) · login/registro Supabase, lib/api.ts + tipos + mocks, proxy por sesión; portafolio y entrega (RF-04); laboratorios y editor de rúbricas (RF-02, RF-03 CA3); fix de hidratación en la navegación · lint, tsc y build OK; pendiente prueba manual en navegador · siguiente paso: evaluación y revisión docente (RF-05/RF-07) · acordar con Rol 2: 404 sin rúbrica vigente, varias entregas por laboratorio, estado "en proceso" tras /evaluar, orden descendente de puntajes, versión vigente dentro de GET /cohortes
