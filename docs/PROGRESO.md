# Progreso del proyecto

| RF | Descripción | Responsable | Estado | Verificado por / fecha |
|---|---|---|---|---|
| RF-01 | Autenticación y usuarios | Rol 2 + Rol 3 | Pendiente | |
| RF-02 | Cohortes y laboratorios | Rol 2 | Pendiente | |
| RF-03 | Gestión de rúbricas | Rol 1 + 2 + 3 | Pendiente | |
| RF-04 | Portafolio académico | Rol 2 + 3 | Pendiente | |
| RF-05 | Evaluación inteligente | Rol 1 + 2 + 3 | Pendiente | |
| RF-06 | Verificación de código / sandbox | Rol 4 | ✅ Completado | Luna Murillo / 2026-11-13 |
| RF-07 | Revisión docente (HITL) | Rol 2 + 3 | Pendiente | |
| RF-08 | Informe integral | Rol 1 + 2 + 3 | Pendiente | |
| RF-09 | Mapa mental | Rol 1 + 2 + 3 | Pendiente | |
| RF-10 | Configuración de IA | Rol 1 + 3 | Pendiente | |
| RF-11 | Proyecto y equipo | Rol 3 | Pendiente | |
| Deploy | URL pública + datos demo | Rol 4 |  ✅ Completado | |

## Bitácora de sesiones
<!-- Formato: fecha · integrante · qué se hizo · siguiente paso -->
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