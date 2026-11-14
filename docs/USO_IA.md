# Uso de IA en el desarrollo (Ingeniería de Software Aumentada)

> Documento obligatorio de la entrega (Condición de ingeniería 1 y Recomendación 7). Cada integrante agrega sus filas a medida que trabaja.

## 1. Herramientas utilizadas
| Herramienta | Para qué la usamos | Integrante(s) |
|---|---|---|
| Claude (chat) | Análisis del caso de uso, documento de requisitos, diseño de agentes | |
| Claude Code + subagentes | Generación de módulos, pruebas, revisión de calidad y seguridad | |
| ChatGPT / Gemini | | |
| GitHub Copilot / Cursor | | |
| Gemini API / Ollama (dentro del producto) | Extracción de rúbricas, evaluación por criterio, informe, mapa | |

## 2. Actividades por fase del ciclo de vida
| Fase | Qué hizo la IA | Qué verificamos/corregimos nosotras |
|---|---|---|
| Requisitos | | |
| Arquitectura | | |
| Desarrollo | | |
| Integración de modelos | | |
| Pruebas y depuración | | |
| Despliegue | | |
| Documentación | | |

## 3. Decisiones técnicas y su justificación
- Stack Next.js + FastAPI + Supabase: …
- Gemini como proveedor por defecto / Ollama como local: requisitos, limitaciones, costos …
- La nota la calcula el backend y no el LLM: …
- Sandbox Docker vs subprocess: …
- Rúbricas de demo: las 4 rúbricas de los laboratorios de demo fueron estructuradas por el equipo (Rol 1) al formato JSON de §7 a partir de los documentos del curso, y validadas automáticamente con el validador del backend (`validar_rubrica`) y con el cálculo de nota (`calcular_nota`) antes de cargarlas en el seed.
  - **Pendiente:** Las ponderaciones de LAB03 y los niveles de desempeño de LAB01 y Manizales Resiliente son propuestas del equipo, pendientes de aprobación docente.

## 4. Problemas encontrados y cómo se resolvieron
| Fecha | Problema (p. ej., la IA generó código que no compilaba, alucinó una librería) | Solución |
|---|---|---|

## 5. Limitaciones de la IA observadas
-

## 6. Costos
| Servicio | Plan | Costo |
|---|---|---|
| Supabase / Vercel / Render | Free | $0 |
| Gemini API | Free tier | $0 (límite de solicitudes por minuto/día) |

## 7. Reflexión del equipo
¿Cómo cambió nuestra forma de programar al pasar de escribir código a dirigir, supervisar y validar agentes?
