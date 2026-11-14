# Progreso del proyecto

| RF | Descripción | Responsable | Estado | Verificado por / fecha |
|---|---|---|---|---|
| RF-01 | Autenticación y usuarios | Rol 2 + Rol 3 | Pendiente | |
| RF-02 | Cohortes y laboratorios | Rol 2 | Pendiente | |
| RF-03 | Gestión de rúbricas | Rol 1 + 2 + 3 | Pendiente | |
| RF-04 | Portafolio académico | Rol 2 + 3 | Pendiente | |
| RF-05 | Evaluación inteligente | Rol 1 + 2 + 3 | 🟡 En progreso: evaluador y citas hechos en `rol1-ia`; pendiente integración Rol 2 | |
| RF-06 | Verificación de código / sandbox | Rol 4 | ✅ Completado | Luna Murillo / 2026-11-13 |
| RF-07 | Revisión docente (HITL) | Rol 2 + 3 | Pendiente | |
| RF-08 | Informe integral | Rol 1 + 2 + 3 | 🟡 En progreso: parte IA (RF-08 CA3, narrativa `generar_informe_narrativo`) hecha en `rol1-ia`; falta integración Rol 2 (cálculo de cifras, API) y Rol 3 (gráficas, PDF) | |
| RF-09 | Mapa mental | Rol 1 + 2 + 3 | 🟡 En progreso: parte IA (RF-09 CA2, `mapear_criterios_a_tematicas`) hecha en `rol1-ia`; falta integración Rol 2 (taxonomía, grafo, API) y Rol 3 (mapa interactivo) | |
| RF-10 | Configuración de IA | Rol 1 + 3 | Pendiente | |
| RF-11 | Proyecto y equipo | Rol 3 | Pendiente | |
| Deploy | URL pública + datos demo | Rol 4 |  ✅ Completado | |

## Bitácora de sesiones
<!-- Formato: fecha · integrante · qué se hizo · siguiente paso -->
- 2026-11-13 · Laura (Rol 1) · base del motor IA: schemas, providers, tests · siguiente paso: prueba real con Gemini y prompts versionados
- 2026-11-13 · Laura (Rol 1) · RF-03 CA1: extracción de rúbricas con IA (prompt extraer_rubrica v1.0, rubricas.py, lectura .md/.docx/.pdf, probado con 3 rúbricas reales en Gemini) · siguiente paso: afinar descriptores de niveles generados (idea: que el LLM extraiga elementos literales y el código arme la plantilla); validador RF-03 CA2 · pendientes: el modelo no respeta siempre los puntajes 5.0/3.5/0.0 de niveles generados (en LAB01 salieron 10/5/0): asignarlos en código; el título de Manizales pierde el subtítulo; descriptores generados pueden traer adjetivos no presentes en el documento
- 2026-11-13 · Laura (Rol 1) · RF-05 (parte IA) en `rol1-ia`: `evaluador.py` (`evaluar_laboratorio`, validación Pydantic + coherencia con la rúbrica, 2 reintentos, `ErrorEvaluacion`), `citas.py` (rapidfuzz `partial_ratio` ≥ 80), prompt `evaluar_laboratorio` v1.0, `generar_texto` en providers; ruff OK, pytest 91 passed · siguiente paso: Rol 2 integra `evaluar_laboratorio` en services/api (guardar `borrador` + versión de rúbrica; `ErrorEvaluacion` → estado `error`)
- 2026-11-13 · Laura (Rol 1) · RF-05: corregidos los hallazgos de las revisiones de calidad y seguridad (neutralización de delimitadores contra inyección en informe, código, verificación y reintentos; verificación solo con conteos numéricos/booleanos y texto libre en bloque NO CONFIABLE; error de validación sin `input_value`; respuesta anterior recortada a 4 000 caracteres; citas con mínimo 3 palabras y 15 caracteres, no verificadas si son más largas que la fuente; topes de 200 000 caracteres de fuente y 500 por cita; fuente normalizada una sola vez; `respuestas_crudas` de cada intento en `ResultadoEvaluacion` y `ErrorEvaluacion`); ruff OK, pytest 110 passed · pendientes para otros roles: **Rol 4**: acordar la forma del dict de resultados de verificación (solo llegan al LLM los valores numéricos/booleanos con sus claves; stdout/stderr y nombres de tests se descartan); **Rol 2**: el API no debe mostrar al estudiante el detalle de `ErrorEvaluacion` (mensaje genérico; el detalle, errores y `respuestas_crudas` van a auditoría)
- 2026-11-13 · Laura (Rol 1) · RF-08 CA3 y RF-09 CA2 (parte IA) en `rol1-ia`: `tematicas.py` (`mapear_criterios_a_tematicas`: todos los criterios, sin extras ni repetidos, solo temáticas de la lista recibida, normalizadas al nombre exacto), `informe.py` (`generar_informe_narrativo` con entrada `DatosDesempeno`: cada acción del plan referencia una temática, competencia o laboratorio de los datos y se rechazan cifras del texto que no estén en los datos), prompts `mapear_tematicas` v1.0 e `informe_narrativo` v1.0, utilidades comunes extraídas a `comun.py` (recorte, delimitadores, reintentos; `evaluador.py` las reexporta sin cambiar su comportamiento); ruff OK, pytest 145 passed · siguiente paso: **Rol 2** arma `DatosDesempeno` con las cifras calculadas (solo evaluaciones publicadas, sin datos personales) y guarda la trazabilidad de `ResultadoMapeo`/`ResultadoInforme`; `ErrorMapeo`/`ErrorInforme` → mensaje genérico al usuario y detalle a auditoría
- 2026-11-13 · Laura (Rol 1) · RF-08 CA3 / RF-09 CA2: corregidos los hallazgos de las revisiones de calidad y seguridad de la Tarea 4 (marcadores con Unicode de ancho completo o caracteres invisibles se neutralizan en los tres prompts; cifras del informe comparadas completas y a la precisión escrita, sin falsos positivos por 0/5, referencias, cantidades y rangos; `DatosDesempeno` rechaza correos y números de 7+ dígitos y vacío da el mismo error que `{}`; topes de rúbrica y temáticas antes de llamar al modelo y mensajes de error recortados; colisiones de nombres neutralizados → `ErrorMapeo`; conceptos, brechas y competencias vacíos → reintento); ruff OK, pytest 178 passed · pendientes para **Rol 2**: el API debe mostrar un mensaje genérico para `ErrorEvaluacion`/`ErrorMapeo`/`ErrorInforme` (el detalle, errores y respuestas crudas van a auditoría); construir `DatosDesempeno` solo con nombres de catálogo (laboratorios, cohortes, temáticas, competencias), nunca con texto libre del usuario

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