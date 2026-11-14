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
<<<<<<< HEAD
- Rangos de nivel en las rúbricas (Rol 1): una recomendación inicial del asistente (usar el extremo superior del rango) habría inflado el nivel "Insuficiente" a 3.4; usamos el punto medio y conservamos la fórmula del documento maestro.
- Descriptores de nivel (Rol 1): pasamos a una plantilla fija con aspectos copiados del documento, porque los descriptores generados traían adjetivos que no estaban en él.
=======
- Rúbricas de demo: las 4 rúbricas de los laboratorios de demo fueron estructuradas por el equipo (Rol 1) al formato JSON de §7 a partir de los documentos del curso, y validadas automáticamente con el validador del backend (`validar_rubrica`) y con el cálculo de nota (`calcular_nota`) antes de cargarlas en el seed.
  - **Pendiente:** Las ponderaciones de LAB03 y los niveles de desempeño de LAB01 y Manizales Resiliente son propuestas del equipo, pendientes de aprobación docente.
- Gestión de usuarios solo para admin (RF-01 CA3): REQUISITOS decía admin/docente; el equipo decidió restringirlo al admin para reducir quién puede cambiar permisos. Un admin no puede quitarse su propio rol ni dejar el sistema sin admin (409), y cada cambio de rol queda en `auditoria`. El correo se copia de `auth.users` a `perfiles` (migración 0002) para no consultar el esquema `auth` desde el backend; limitación: si el usuario cambia su correo en Supabase Auth, la copia no se actualiza sola.
- Configuración de IA (RF-10): solo el admin puede verla y cambiarla (REQUISITOS decía docente; el equipo decidió restringirla). Las claves y la URL base nunca se devuelven ni se guardan en la base de datos: la API solo indica si están configuradas (sí/no). El proveedor y el modelo se validan contra una lista blanca del backend (Gemini: lista fija en `services/config_ia.py` con `gemini-3.5-flash-lite`, predeterminado y probado, y `gemini-3.6-flash`, permitido pero sin probar con nuestros prompts; `gemini-2.5-flash` se quitó porque Google lo retiró; la API indica cuáles están probados en `modelos_probados`. OpenAI-compatible: variable `OPENAI_COMPAT_MODELOS` y un patrón seguro de nombre). Una temperatura fuera de 0–0,2 se rechaza con 422 en lugar de recortarse. Cada cambio queda en `auditoria`; guardar el mismo valor no genera registro. El modelo por defecto se alineó a `gemini-3.5-flash-lite` en `config.py` y en el seed, igual que en `providers.py` y en `.env.example`. El botón "Probar conexión" hace una sola llamada mínima con un límite total de 10 s y siempre responde con un mensaje genérico; el detalle técnico solo va a `auditoria`, con URL, tokens y claves tachados, porque los errores de los SDK pueden incluir la URL base. La prueba construye el proveedor con `max_retries=0` (sin reintentos por JSON inválido); evaluación, informe y mapa conservan los reintentos por defecto. Al medirla contra un puerto cerrado vimos que sigue tardando ~7–10 s por los reintentos internos del SDK de OpenAI, que no controla `max_retries`; quedó anotado para Rol 1 en PROGRESO.
- Evaluación con IA (RF-05): corre en segundo plano (`BackgroundTasks`, sin colas externas) y responde 202 con estado `procesando`. La nota la calcula solo el backend (`nota.py`) con la versión de rúbrica de la entrega; el backend además valida que la IA devuelva todos los criterios con niveles existentes. Las respuestas crudas del LLM se guardan solo en `auditoria` (la columna `evaluaciones.respuesta_cruda` queda vacía) y, si algo falla, el usuario solo ve un mensaje genérico. El estudiante solo ve sus evaluaciones publicadas y sin datos internos del modelo (proveedor, modelo, temperatura, versión de prompt, nivel original de la IA). Los resultados de verificación se sanean (solo números y booleanos) antes de enviarlos al LLM, y no se usa `entrega.extras` porque lo escribe el estudiante. El evaluador de Rol 1 se carga de forma perezosa mediante un adaptador, para que el backend funcione aunque aún no esté integrado.
- Revisión docente (RF-07, Human-in-the-Loop): el docente pasa la evaluación a revisión, ajusta niveles con motivo obligatorio (la nota la recalcula el backend; el nivel propuesto por la IA nunca se sobrescribe), edita la retroalimentación conservando el texto original de la IA en columnas separadas (`retroalimentacion_docente`, migración 0004), aprueba y publica. Las transiciones permitidas son `borrador → en_revision → aprobada → publicada`; después de aprobar no se puede ajustar ni editar. Cada acción queda en `auditoria` en la misma transacción que el cambio, y la traza (solo docente) muestra todos los eventos en orden con las respuestas crudas del LLM, filtrando por precaución cualquier campo que parezca una clave. Decisiones: listado paginado `{items, total, limit, offset}`; ajustar al mismo nivel no genera cambios ni auditoría; en la edición `""` se rechaza, `null` vuelve al texto de la IA y un texto igual al de la IA cuenta como sin edición.
- Informe integral y mapa de conocimiento (RF-08, RF-09): todos los números (notas por laboratorio, promedios por cohorte, general, por competencia y por temática, evolución y niveles de dominio) los calcula el backend con aritmética exacta y ROUND_HALF_UP; la IA solo redacta la narrativa (competencias desarrolladas, brechas, plan de fortalecimiento) y relaciona criterios con temáticas. A la IA se le envían solo datos académicos agregados, sin nombre, correo ni ids de personas, y aunque devuelva cifras no se usan. Solo cuentan evaluaciones publicadas (por laboratorio, la más reciente). Decisiones: la narrativa se genera dentro del GET (sin botón aparte) y se guarda en `cache_ia` hasta que cambien los números o la versión del prompt; el mapeo a temáticas se guarda por versión de rúbrica; si la IA falla se muestra un mensaje genérico, el detalle va a auditoría y el siguiente GET reintenta; sin evaluaciones publicadas el promedio general es null (no 0,0) y no se llama a la IA; el dominio es un promedio simple del puntaje normalizado × 5 de los criterios; niveles: bajo < 3,0, medio 3,0–3,9, alto ≥ 4,0; el estudiante y el docente ven el mismo informe y mapa. Si el mapeo de la IA no está disponible, el mapa se agrupa por competencia con un aviso.
>>>>>>> rol2-backend

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
- Rol 1 (prueba real del evaluador con Gemini 3.5 Flash-Lite, 2026-11-14): para los criterios sin evidencia, el modelo citó el título del informe y la cita salió "verificada" sin respaldar nada. Además, el validador de cifras marcaba "Python 3.12" como una cifra inventada. Lo corregimos: ahora se permiten evidencias vacías solo en el nivel más bajo (prompt 1.1) y las versiones de software se reconocen como tales.
- Rol 1: el código generado tenía problemas de seguridad y validación (inyección mediante marcadores, citas cortas siempre verificadas, comprobación de cifras con falsos positivos y negativos, falta de topes de tamaño).

## 6. Costos
| Servicio | Plan | Costo |
|---|---|---|
| Supabase / Vercel / Render | Free | $0 |
| Gemini API | Free tier | $0 (límite de solicitudes por minuto/día) |

## 7. Reflexión del equipo
¿Cómo cambió nuestra forma de programar al pasar de escribir código a dirigir, supervisar y validar agentes?
