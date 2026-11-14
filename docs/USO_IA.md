# Uso de IA en el desarrollo (Ingeniería de Software Aumentada)

> Documento obligatorio de la entrega (Condición de ingeniería 1 y Recomendación 7). Cada integrante agrega sus filas a medida que trabaja.

## 1. Herramientas utilizadas
| Herramienta | Para qué la usamos | Integrante(s) |
|---|---|---|
| Claude (chat) | Análisis del caso de uso, documento de requisitos, diseño de agentes | |
| Claude Code + subagentes | Generación de módulos, pruebas, revisión de calidad y seguridad | Laura (Rol 1): evaluador, mapeo a temáticas, narrativa del informe y revisiones de calidad y seguridad antes de cada commit |
| ChatGPT / Gemini | | |
| GitHub Copilot / Cursor | | |
| Gemini API / Ollama (dentro del producto) | Extracción de rúbricas, evaluación por criterio, informe, mapa | Laura (Rol 1): extracción de rúbricas con Gemini (RF-03 CA1) |

## 2. Actividades por fase del ciclo de vida
| Fase | Qué hizo la IA | Qué verificamos/corregimos nosotras |
|---|---|---|
| Requisitos | | |
| Arquitectura | | |
| Desarrollo | Rol 1: Claude Code escribió el evaluador con reintentos y verificación de citas (RF-05), el mapeo de criterios a temáticas (RF-09 CA2) y la narrativa del informe (RF-08 CA3). | Probamos todo con FakeProvider. El asistente de chat numeró al revés RF-08 CA3 y RF-09 CA2; lo detectó el agente al comprobarlo en REQUISITOS.md. |
| Integración de modelos | Rol 1: Gemini extrae rúbricas desde .md, .docx y .pdf (RF-03 CA1). | La probamos con 3 rúbricas reales del curso. Corregimos puntajes de niveles que no respetaban 5.0/3.5/0.0 (en LAB01 salieron 10/5/0), el título de Manizales que perdía el subtítulo y descriptores con adjetivos que no estaban en el documento. Pendiente: primera prueba real con Gemini del evaluador, el mapeo y el informe. |
| Pruebas y depuración | Rol 1: revisiones automáticas de calidad y seguridad de cada tarea antes del commit. | Verificamos con ruff y pytest (178 pruebas), revisores de calidad y seguridad por tarea, y rúbricas de demo validadas con Pydantic. Los hallazgos de las revisiones de las Tareas 3 y 4 se corrigieron con pruebas (ver §4). |
| Despliegue | | |
| Documentación | | |

## 3. Decisiones técnicas y su justificación
- Stack Next.js + FastAPI + Supabase: …
- Gemini como proveedor por defecto / Ollama como local: requisitos, limitaciones, costos …
- La nota la calcula el backend y no el LLM: …
- Sandbox Docker vs subprocess: …
- Rangos de nivel en las rúbricas (Rol 1): una recomendación inicial del asistente (usar el extremo superior del rango) habría inflado el nivel "Insuficiente" a 3.4; usamos el punto medio y conservamos la fórmula del documento maestro.
- Descriptores de nivel (Rol 1): pasamos a una plantilla fija con aspectos copiados del documento, porque los descriptores generados traían adjetivos que no estaban en él.

## 4. Problemas encontrados y cómo se resolvieron
| Fecha | Problema (p. ej., la IA generó código que no compilaba, alucinó una librería) | Solución |
|---|---|---|
| 2026-11-13 | Rol 1: el extractor no respetaba los puntajes 5.0/3.5/0.0 de los niveles generados (en LAB01 salieron 10/5/0). | Usamos rúbricas de demo revisadas a mano. Pendiente: asignar los puntajes desde el código. |
| 2026-11-13 | Rol 1: el título de la rúbrica de Manizales perdía el subtítulo. | Usamos la rúbrica de demo revisada a mano. Pendiente: corregirlo en el extractor. |
| 2026-11-13 | Rol 1: los descriptores generados traían adjetivos que no estaban en el documento. | Pasamos a una plantilla fija con aspectos copiados del documento. |
| 2026-11-13 | Rol 1: una recomendación inicial del asistente sobre los rangos de nivel (usar el extremo superior) habría inflado el nivel "Insuficiente" a 3.4. | Usamos el punto medio y conservamos la fórmula del documento maestro. |
| 2026-11-13 | Rol 1: Gemini devolvió error 503 por saturación durante una prueba. | Reintentamos una vez. |
| 2026-11-13 | Rol 1: la revisión de seguridad de la Tarea 3 encontró 2 problemas de gravedad media: inyección de instrucciones mediante marcadores en el informe del estudiante y citas muy cortas que siempre salían verificadas. | Los corregimos con pruebas. |
| 2026-11-13 | Rol 1: la revisión de la Tarea 4 encontró que la comprobación de cifras aceptaba una nota inventada pegada a letras ("4.9pts") y rechazaba textos normales ("escala de 0 a 5"); también faltaban topes de tamaño y no se neutralizaban marcadores Unicode. | Lo corregimos con pruebas. |
| 2026-11-13 | Rol 1: el asistente de chat numeró al revés RF-08 CA3 y RF-09 CA2. | Lo detectó el agente al comprobarlo en REQUISITOS.md. |

## 5. Limitaciones de la IA observadas
- Rol 1: el extractor de rúbricas no respetó los puntajes indicados para los niveles (en LAB01 salieron 10/5/0 en vez de 5.0/3.5/0.0).
- Rol 1: los descriptores generados agregaron adjetivos que no estaban en el documento.
- Rol 1: el asistente dio una recomendación sobre rangos de nivel que habría inflado el nivel "Insuficiente" a 3.4, y el asistente de chat numeró al revés RF-08 CA3 y RF-09 CA2.
- Rol 1: Gemini devolvió error 503 por saturación durante una prueba.
- Rol 1: el código generado tenía problemas de seguridad y validación (inyección mediante marcadores, citas cortas siempre verificadas, comprobación de cifras con falsos positivos y negativos, falta de topes de tamaño).

## 6. Costos
| Servicio | Plan | Costo |
|---|---|---|
| Supabase / Vercel / Render | Free | $0 |
| Gemini API | Free tier | $0 (límite de solicitudes por minuto/día) |

## 7. Reflexión del equipo
¿Cómo cambió nuestra forma de programar al pasar de escribir código a dirigir, supervisar y validar agentes?
