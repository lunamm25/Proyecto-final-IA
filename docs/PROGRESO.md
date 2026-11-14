# Progreso del proyecto

| RF | Descripción | Responsable | Estado | Verificado por / fecha |
|---|---|---|---|---|
| RF-01 | Autenticación y usuarios | Rol 2 + Rol 3 | En progreso (backend listo: CA2, CA3, CA4; falta frontend) | |
| RF-02 | Cohortes y laboratorios | Rol 2 | En progreso | |
| RF-03 | Gestión de rúbricas | Rol 1 + 2 + 3 | En progreso (backend: validador y versionado; Rol 1: extracción) | |
| RF-04 | Portafolio académico | Rol 2 + 3 | Pendiente | |
| RF-05 | Evaluación inteligente | Rol 1 + 2 + 3 | En progreso (backend: lanzar en segundo plano, nota, borrador/error, consulta; falta material real de la entrega y evaluador de Rol 1 en main) | |
| RF-06 | Verificación de código / sandbox | Rol 4 | ✅ Completado | Luna Murillo / 2026-11-13 |
| RF-07 | Revisión docente (HITL) | Rol 2 + 3 | En progreso (backend listo: revisar, ajustar, editar retroalimentación, aprobar, publicar, listado y traza; falta frontend) | |
| RF-08 | Informe integral | Rol 1 + 2 + 3 | Pendiente | |
| RF-09 | Mapa mental | Rol 1 + 2 + 3 | Pendiente | |
| RF-10 | Configuración de IA | Rol 1 + 3 | Pendiente | |
| RF-11 | Proyecto y equipo | Rol 3 | Pendiente | |
| Deploy | URL pública + datos demo | Rol 4 |  ✅ Completado | |

## Bitácora de sesiones
<!-- Formato: fecha · integrante · qué se hizo · siguiente paso -->
- 2026-11-13 · Mariana (Rol 2) · Se cargaron en el seed los 4 laboratorios de demo (C1-01 Parcial 1 Fundamentos de IA, C1-02 Manizales Resiliente, C2-01 Laboratorio 01 Automatización de archivos, C2-02 Laboratorio 03 Agente con Ollama) con sus rúbricas de `backend/rubricas_demo/` como versión 1 aprobada (validadas con `validar_rubrica` y `calcular_nota`); se borraron de Supabase los 6 laboratorios `[PROVISIONAL]` (sin entregas) · Siguiente paso: correr `python seed.py` contra Supabase y revisar `GET /api/cohortes` y la rúbrica vigente de cada laboratorio en `/docs`.

> **Nota:** Las ponderaciones de LAB03 y los niveles de desempeño de LAB01 y Manizales Resiliente son propuestas del equipo, pendientes de aprobación docente.

- 2026-11-13 · Laura (Rol 1) · base del motor IA: schemas, providers, tests · siguiente paso: prueba real con Gemini y prompts versionados
- 2026-11-13 · Laura (Rol 1) · RF-03 CA1: extracción de rúbricas con IA (prompt extraer_rubrica v1.0, rubricas.py, lectura .md/.docx/.pdf, probado con 3 rúbricas reales en Gemini) · siguiente paso: afinar descriptores de niveles generados (idea: que el LLM extraiga elementos literales y el código arme la plantilla); validador RF-03 CA2 · pendientes: el modelo no respeta siempre los puntajes 5.0/3.5/0.0 de niveles generados (en LAB01 salieron 10/5/0): asignarlos en código; el título de Manizales pierde el subtítulo; descriptores generados pueden traer adjetivos no presentes en el documento

## 2026-11-13 — Luna (Rol 4 DevOps/Calidad)

- ✅ RF-06: Sandbox seguro de ejecución (módulo `backend/app/sandbox/`)
  - `SandboxRunner` con método `ejecutar_zip(archivo_zip: bytes) -> dict`
  - Validaciones: ZIP ≤ 20 MB, ≤ 2000 archivos, ≤ 100 MB descomprimido
  - Protección: zip-slip detectado, zip-bomb limitado, entorno aislado vacío
  - Ejecución: timeout 10s, captura stdout/stderr, código de salida
  - Endpoint POST `/api/sandbox/ejecutar` con multipart file upload
  - Tests: 14 casos (válido, tamaño, archivos, contenido, zip-slip, timeout, stderr, código salida, etc.)
  - Ruff check: ✅ pass
  - Pytest: ✅ 62/62 tests pass (14 nuevos)
  - Siguiente: integración con verificacion estatico + endpoint de evaluación

- ✅ Creado workflow de CI en `.github/workflows/ci.yml` con jobs para backend (ruff + pytest) y frontend (lint + tsc + build)
- ✅ Corregida ruta `cache-dependency-path` para caché de npm en CI
- ✅ PR `rol4-devops` → `main` creado y mergeado con todos los checks en verde
- ✅ Frontend desplegado en Vercel: https://proyecto-final-ia-vaiw.vercel.app
- ✅ Revisión del PR #1 de Laura (Rol 1) — cambios aprobados y mergeados a `main`

- 2026-11-14 · Mariana (Rol 2) · Gestión de usuarios y roles (RF-01 CA3): `GET /api/usuarios` y `PATCH /api/usuarios/{id}/rol`, **solo admin** (decisión del equipo; REQUISITOS §11 y RF-01 CA3 actualizados, antes decían admin/docente). 409 si un admin se quita su propio rol de admin o si se dejaría el sistema sin admin; mismo rol → 200 sin auditoría; cada cambio queda en `auditoria`. Migración `0002_perfiles_correo.sql` (columna `correo` en `perfiles`). 256 tests en verde · Siguiente paso: aplicar la 0002 en Supabase (obligatorio antes de usar esta versión del backend) y nombrar al primer admin.

- 2026-11-14 · Mariana (Rol 2) · Merge de `main` en `rol2-backend` (cambios de Laura: motor de IA y extracción de rúbricas; de Luna: sandbox y CI). Conflictos en `main.py` (se integró el router `sandbox` en `crear_app`) y `PROGRESO.md`. RF-03 pasa a "En progreso" (backend: validador y versionado; Rol 1: extracción). Excepción de ruff N818 solo para `app/ia/providers.py` en `backend/pyproject.toml`. 320 tests en verde · Pendientes para el equipo: `POST /api/sandbox/ejecutar` es público y no está en §11 (avisar a Luna); acordar cuál copia de `rubricas_demo` es la fuente.

- 2026-11-14 · Mariana (Rol 2) · RF-05: `POST /api/entregas/{id}/evaluar` (202 + `procesando`, tarea de fondo con BackgroundTasks, 409 doble lanzamiento) y `GET /api/evaluaciones/{id}` (estudiante solo publicadas; 403 "pendiente de revisión docente"). Nota calculada solo por `nota.py` con la versión de rúbrica de la entrega; respuestas crudas solo en `auditoria`; adaptador perezoso al evaluador de Rol 1. Migración `0003_estado_procesando.sql` **pendiente de aplicar en Supabase**. 382 tests en verde · Siguiente paso: material real de la entrega (PDF desde Storage, resumen de código, verificación de Rol 4) con `POST /api/entregas`; esperar `app/ia/evaluador.py` en main.

- 2026-11-14 · Mariana (Rol 2) · RF-07 revisión docente (HITL): `GET /api/evaluaciones` (listado paginado), `POST /{id}/revisar`, `PATCH /{id}/criterios/{criterio_id}` (motivo obligatorio, nota recalculada solo por `nota.py`), `PATCH /{id}/retroalimentacion` (conserva el original de la IA), `POST /{id}/aprobar`, `POST /{id}/publicar` y `GET /{id}/traza`. Cada acción queda en `auditoria` en la misma transacción; el lanzamiento también se registra. REQUISITOS §10 y §11 actualizados. 517 tests en verde · **Pendiente en Supabase: aplicar las migraciones 0003 (`estado procesando`) y 0004 (`retroalimentacion_docente`)** — sin ellas fallan las rutas de evaluaciones · Siguiente paso: `POST /api/entregas` con material real (PDF desde Storage).
