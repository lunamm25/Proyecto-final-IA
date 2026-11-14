# Asesor Pedagógico Inteligente — Documento Maestro de Requisitos

> Fuente única de verdad del proyecto. Todo agente y todo integrante lo lee antes de implementar.
> Proyecto final Profundización I – IA · Universidad de Manizales · Ingeniería de Sistemas y Telecomunicaciones
> Entrega: URL pública funcional · Socialización: martes 17 de noviembre de 2026 (horario de clase)
> Nivel acordado: **FUNCIONAL Y SÓLIDO** (cumplir las 7 funcionalidades y las 6 condiciones de ingeniería, sin sobreingeniería).

---

## 1. Visión

Plataforma web en la que un estudiante sube las evidencias de sus laboratorios (cohortes 1 y 2 del curso de IA) junto con la descripción y la rúbrica de cada uno. La IA analiza las evidencias criterio por criterio, cita evidencias concretas y propone un nivel de desempeño. **El backend calcula la nota (0,0–5,0) con las ponderaciones de la rúbrica.** El docente revisa, ajusta y aprueba antes de publicar (Human-in-the-Loop). La plataforma consolida un informe integral del aprendizaje y un mapa mental interactivo de competencias en IA.

Principios: evaluaciones **consistentes, explicables, trazables y validadas por el docente**.

## 2. Usuarios y roles

| Rol | Puede |
|---|---|
| **Estudiante** | Subir entregas a su portafolio, lanzar la evaluación preliminar, ver evaluaciones **publicadas**, ver su informe y su mapa mental, descargar ambos. |
| **Docente** | Gestionar cohortes, laboratorios y rúbricas (cargar, corregir, aprobar versión); ver todas las entregas; revisar, ajustar (con justificación obligatoria), aprobar y publicar evaluaciones; configurar el proveedor de IA. |
| **Admin** | Lo del docente + gestionar usuarios y roles. (Puede ser el mismo docente en la demo.) |

## 3. Alcance

### Incluido (MVP que se entrega)
- Autenticación (email + contraseña) y gestión de usuarios con roles.
- Cohortes 1 y 2 con sus laboratorios (descripción + objetivos).
- Rúbricas: carga (PDF/DOCX/texto), extracción con IA a estructura, validación automática, edición manual, versionado.
- Portafolio por estudiante y laboratorio: PDF de informe (texto legible) + código (ZIP o URL de GitHub pública) + rúbrica asociada (versión congelada). Imágenes opcionales.
- Evaluación inteligente por criterio + verificación técnica de código + nota calculada por backend.
- Revisión, ajuste y aprobación docente con historial.
- Informe integral (visualizar + descargar PDF).
- Mapa mental interactivo (navegar, explorar, descargar PNG/JSON).
- Página "Proyecto y equipo": abstract + foto, nombre y rol de las 4 integrantes.
- Proveedor de IA configurable (nube o local).
- Despliegue con URL pública.

### Excluido explícitamente (documentar como trabajo futuro)
- Análisis de video y audio (se aceptan como enlace, no se analizan).
- Ejecución de código en lenguajes distintos de Python (para otros lenguajes solo análisis estático/métricas).
- Integración con LMS (Moodle), notificaciones por correo, pagos, app móvil.
- Microservicios, Kubernetes, colas distribuidas. **Un frontend + un backend + Supabase.**

## 4. Stack tecnológico (decidido)

| Capa | Tecnología | Despliegue |
|---|---|---|
| Frontend | Next.js 14+ (App Router) + TypeScript + Tailwind CSS + shadcn/ui; React Flow (mapa mental); Recharts (gráficas) | Vercel |
| Backend | Python 3.11 + FastAPI + **Pydantic v2** + SQLAlchemy 2 | Render (web service) |
| Datos | Supabase: Postgres + Auth + Storage (bucket privado) | Supabase cloud (free) |
| IA | Capa `LLMProvider` con: **Gemini** (modelo Flash vigente, p. ej. `gemini-3.5-flash-lite`; free tier, multimodal) y **OpenAI-compatible** (Ollama local, Groq, OpenRouter) | Configurable por variables de entorno y panel docente |
| Verificación de código | `ast` + `ruff` + `radon` (estático, nunca ejecuta) · `pytest` en sandbox | Backend |

Justificación breve (para la documentación): Pydantic es obligatorio → Python en backend; Supabase da login, BD y archivos sin montar servidores; Gemini tiene capa gratuita y lee PDF e imágenes; Ollama permite modelo local sin costo; Vercel/Render despliegan desde GitHub.

## 5. Requisitos funcionales

Cada RF tiene criterios de aceptación (CA). Un RF está **terminado** solo si todos sus CA pasan y está verificado (ver CLAUDE.md).

### RF-01 Autenticación y usuarios
- CA1: registro e inicio de sesión con email/contraseña (Supabase Auth).
- CA2: tabla `perfiles` con nombre y rol (`estudiante` por defecto).
- CA3: el admin/docente puede cambiar el rol de un usuario.
- CA4: el backend valida el JWT de Supabase en cada petición y aplica permisos por rol (401/403).

### RF-02 Cohortes y laboratorios (Entrada de información)
- CA1: CRUD de laboratorios por cohorte (código, título, descripción, objetivos) — solo docente.
- CA2: cada laboratorio tiene exactamente una rúbrica activa (versión aprobada).
- CA3: datos semilla con las cohortes 1 y 2 y sus laboratorios reales del curso.

### RF-03 Gestión de rúbricas
- CA1: subir rúbrica en PDF/DOCX/texto; la IA la convierte a `RubricaSchema` (JSON validado con Pydantic).
- CA2: el backend valida y lista **inconsistencias**: ponderaciones que no suman 100 %, criterios sin niveles, niveles sin puntaje o sin descriptor, puntajes no ordenados, criterios duplicados, competencia vacía.
- CA3: el docente edita la rúbrica en un formulario y ve las inconsistencias en vivo.
- CA4: no se puede aprobar ni evaluar con una rúbrica con inconsistencias.
- CA5: al aprobar se crea una **versión inmutable** (`rubrica_versiones`); editar después crea una versión nueva.

### RF-04 Portafolio académico
- CA1: el estudiante crea una entrega por laboratorio: PDF del informe (obligatorio, texto extraíble), código (ZIP ≤ 20 MB **o** URL pública de GitHub), imágenes/video/presentación (opcionales).
- CA2: si el PDF no tiene texto extraíble, se rechaza con un mensaje claro.
- CA3: la entrega queda asociada a su laboratorio y a la **versión de rúbrica vigente** en ese momento.
- CA4: vista del portafolio agrupada por cohorte → laboratorio, con el estado de cada entrega (sin evaluar, evaluada-borrador, en revisión, publicada).
- CA5: los archivos se guardan en un bucket privado; solo se accede con URL firmada temporal.

### RF-05 Evaluación inteligente por laboratorio
- CA1: el pipeline: extraer texto del PDF → preparar el código (descomprimir/clonar con límites) → **verificación técnica** → prompt al LLM con descripción, objetivos, rúbrica, texto, resumen del código y resultados técnicos → respuesta validada con `EvaluacionLLMSchema`.
- CA2: por cada criterio la IA devuelve: nivel elegido (de los niveles de la rúbrica), evidencias citadas (fragmento + fuente), justificación, fortalezas, debilidades, recomendación.
- CA3: **verificación anti-alucinación**: cada evidencia citada debe existir en el material (coincidencia aproximada ≥ 0,8). Las evidencias no encontradas se marcan como "no verificadas" y se muestran al docente.
- CA4: si la respuesta no valida contra el esquema, se reintenta hasta 2 veces enviando el error; si falla, la evaluación queda en estado `error` con el detalle.
- CA5: **la nota la calcula el backend** (sección 8). El LLM nunca devuelve ni calcula la nota.
- CA6: el resultado queda en estado `borrador` y lo ve el docente; el estudiante ve "pendiente de revisión docente".

### RF-06 Verificación objetiva del código
- CA1: análisis estático sin ejecutar: sintaxis (`ast.parse`) por archivo Python, `ruff` (errores/advertencias), complejidad (`radon cc`), conteo de archivos/líneas, presencia de README, requirements y tests.
- CA2: si hay tests (`test_*.py`), se ejecutan con `pytest` **dentro del sandbox** (sección 9) y se registra aprobados/fallidos.
- CA3: los resultados se guardan en `verificaciones_codigo` y se pasan al LLM como evidencia objetiva.
- CA4: para lenguajes distintos de Python: solo métricas y presencia de archivos; se informa como limitación.

### RF-07 Revisión docente (Human-in-the-Loop)
- CA1: el docente ve, por criterio: nivel propuesto, evidencias (verificadas/no verificadas), justificación y resultados técnicos.
- CA2: puede cambiar el nivel de cualquier criterio y editar la retroalimentación; **la justificación del cambio es obligatoria**. La nota se recalcula en el backend.
- CA3: flujo de estados: `borrador → en_revision → aprobada → publicada` (y `error`). Solo `publicada` es visible para el estudiante.
- CA4: cada ajuste queda en `auditoria` (quién, cuándo, valor anterior, valor nuevo, motivo).

### RF-08 Informe integrado del aprendizaje
- CA1: consolida las evaluaciones **publicadas** de ambas cohortes del estudiante.
- CA2: el backend calcula: nota por laboratorio, promedio por cohorte, promedio general, nivel de dominio por competencia y evolución (cohorte 1 → cohorte 2).
- CA3: la IA redacta (esquema `InformeNarrativoSchema`): competencias desarrolladas, brechas y **plan personalizado de fortalecimiento** (acciones, recursos, prioridad). Los números los pone el backend, no la IA.
- CA4: se visualiza en la web con gráficas (evolución, dominio por competencia) y se descarga en PDF.

### RF-09 Mapa mental interactivo de competencias
- CA1: taxonomía base de temáticas de IA (semilla editable) — p. ej. Fundamentos de IA, Aprendizaje automático, LLMs, Ingeniería de prompts, Modelos locales (Ollama/LM Studio), Agentes de IA, RAG, Visión artificial, Series temporales/APIs de datos, Desarrollo de software aumentado / vibe coding, Ética y verificación.
- CA2: la IA asocia cada criterio/competencia evaluada con una o varias temáticas (`MapeoTematicasSchema`).
- CA3: el backend construye el grafo: temática → subtemas/conceptos → laboratorios donde se aplicó; cada nodo con nivel de dominio (color), evidencias y aspectos por profundizar.
- CA4: interacción: zoom, arrastre, expandir/colapsar, clic en un nodo abre panel con detalle; búsqueda/filtro por nivel.
- CA5: descarga como PNG y JSON.

### RF-10 Configuración de IA
- CA1: el docente elige proveedor (Gemini / OpenAI-compatible) y modelo desde un panel; la URL base y la clave salen de variables de entorno (nunca se muestran en la interfaz).
- CA2: botón "Probar conexión".
- CA3: cada evaluación guarda proveedor, modelo, temperatura y versión del prompt.

### RF-11 Presentación del proyecto y equipo
- CA1: página pública con abstract (objetivos, funcionalidades, tecnologías, aportes).
- CA2: tarjetas con foto, nombre y rol de: Laura Valentina Suarez (Rol 1 – IA y motor de evaluación), Mariana Otalvaro Gutierrez (Rol 2 – Backend y lógica de negocio), Daniela Garcia Valencia (Rol 3 – Frontend y experiencia interactiva), Luna Murillo Moreno (Rol 4 – DevOps, verificación y calidad).
- CA3: sección "Cómo usamos IA para construir esto" enlazando `docs/USO_IA.md`.

## 6. Requisitos no funcionales

| ID | Requisito | Cómo se verifica |
|---|---|---|
| RNF-01 Seguridad | JWT validado en backend; permisos por rol; bucket privado + URLs firmadas; claves solo en variables de entorno; CORS restringido al dominio del frontend; límites de tamaño de archivo; validación de tipos MIME. | Revisor de seguridad + tests de permisos |
| RNF-02 Reproducibilidad | `temperature ≤ 0.2`; prompts versionados en `backend/app/ia/prompts/` con versión; salidas validadas con Pydantic; nota determinista. | Tests del cálculo de nota |
| RNF-03 Trazabilidad | Cada evaluación guarda: entrega, versión de rúbrica, proveedor/modelo, versión de prompt, respuesta cruda, respuesta validada, verificaciones, ajustes docentes. | Inspección en BD / vista de traza |
| RNF-04 Rendimiento | Evaluación de un laboratorio < 2 min; la UI muestra progreso (la evaluación corre en tarea de fondo y el frontend consulta el estado). | Prueba manual cronometrada |
| RNF-05 Usabilidad | Interfaz en español, responsive, estados de carga/vacío/error en cada pantalla, mensajes claros. | Revisión de calidad |
| RNF-06 Disponibilidad demo | URL pública estable el martes; datos de demo cargados; plan B (video corto) por si la nube falla. | Checklist de despliegue |
| RNF-07 Calidad de código | Ruff + mypy básico en backend; ESLint + `tsc` en frontend; tests de las reglas críticas. | CI en GitHub Actions |
| RNF-08 Protección de datos | Estudiante solo ve lo suyo; docente ve todo; no se envían datos personales innecesarios al LLM (se envía el contenido académico, no el correo). | Tests de permisos |

## 7. Esquemas Pydantic (contrato con el LLM)

```python
# backend/app/ia/schemas.py  (resumen — implementar completo)
class NivelDesempeno(BaseModel):
    nombre: str                 # "Excelente", "Bueno", ...
    puntaje: float              # valor numérico del nivel (p. ej. 5, 4, 3...)
    descriptor: str

class Criterio(BaseModel):
    id: str
    competencia: str
    nombre: str
    ponderacion: float          # porcentaje; la suma de todos = 100
    niveles: list[NivelDesempeno]  # al menos 2, puntajes distintos

class RubricaSchema(BaseModel):
    titulo: str
    criterios: list[Criterio]

class Evidencia(BaseModel):
    fragmento: str              # cita textual corta del material
    fuente: Literal["informe", "codigo", "verificacion", "imagen"]
    ubicacion: str | None       # página, archivo:línea, etc.

class EvaluacionCriterio(BaseModel):
    criterio_id: str
    nivel_elegido: str          # DEBE ser uno de los nombres de nivel del criterio
    evidencias: list[Evidencia] # mínimo 1, salvo en el nivel de menor puntaje (vacía = sin evidencia)
    justificacion: str
    fortalezas: list[str]
    debilidades: list[str]
    recomendacion: str

class EvaluacionLLMSchema(BaseModel):
    criterios: list[EvaluacionCriterio]   # uno por cada criterio de la rúbrica, sin faltantes ni extras
    aprendizajes_identificados: list[str]
    como_aplico_conocimientos: str
    aspectos_a_fortalecer: list[str]
    retroalimentacion_general: str
    # ⚠️ NO hay campo "nota": la calcula el backend.
```

Validaciones adicionales en backend (no confiar en el LLM): todos los `criterio_id` existen y no faltan; `nivel_elegido` pertenece a los niveles del criterio; sin evidencias solo se admite el nivel de menor puntaje; los niveles de un mismo criterio no pueden tener el mismo nombre; evidencias verificadas contra el material.

Otros esquemas: `InformeNarrativoSchema` (competencias_desarrolladas, brechas, plan_fortalecimiento[{accion, recurso, prioridad, competencia}], conclusion) y `MapeoTematicasSchema` ([{criterio_id, tematicas[], conceptos[]}]).

## 8. Cálculo de la nota (backend, determinista)

```
Para cada criterio i:
  puntaje_i     = puntaje del nivel elegido (o ajustado por el docente)
  max_i, min_i  = puntaje máximo y mínimo entre los niveles del criterio
  normalizado_i = (puntaje_i - min_i) / (max_i - min_i)      # 0..1
nota = Σ (ponderacion_i / 100) × normalizado_i × 5.0
nota = redondear a 1 decimal (ROUND_HALF_UP), acotada a [0.0, 5.0]
```
Decisión a documentar: el nivel más bajo equivale a 0,0. *(Si el profesor prefiere `puntaje_i / max_i`, cambiar solo esta función y sus tests.)*
Tests obligatorios: suma 100 %, todo máximo = 5,0, todo mínimo = 0,0, caso mixto conocido, redondeo, rúbrica inválida lanza error.

## 9. Sandbox de ejecución de código

- Código del estudiante = **no confiable**. El análisis estático (`ast`, `ruff`, `radon`) nunca lo ejecuta.
- Ejecución (`pytest`) solo a través de la interfaz `SandboxRunner`:
  - `DockerSandbox` (si hay Docker disponible: local o VPS): `--network none --memory 512m --cpus 1 --pids-limit 128 --read-only`, carpeta temporal montada, usuario sin privilegios, timeout 60 s.
  - `SubprocessSandbox` (fallback en Render): proceso hijo con `resource.setrlimit` (CPU 30 s, memoria 512 MB, tamaño de archivo, nº de procesos), timeout, entorno vacío (sin variables secretas), directorio temporal que se borra, proxies apuntando a un host inválido.
  - Variable `SANDBOX_EJECUTAR_TESTS=true|false` para desactivar la ejecución en producción si hace falta.
- Límites de entrada: ZIP ≤ 20 MB, ≤ 2.000 archivos, protección contra zip-slip y zip-bomb (tamaño descomprimido ≤ 100 MB); GitHub: `git clone --depth 1` con timeout, solo repos públicos.
- **Limitación a documentar honestamente:** en Render (sin Docker) el aislamiento de red no es total; por eso los tests se ejecutan con límites estrictos y pueden desactivarse.

## 10. Modelo de datos (Postgres / Supabase)

```
perfiles(id uuid PK = auth.users.id, nombre, rol, foto_url, creado_en)
cohortes(id, nombre, numero)                                 -- 1 y 2
laboratorios(id, cohorte_id FK, codigo, titulo, descripcion, objetivos)
rubricas(id, laboratorio_id FK UNIQUE)
rubrica_versiones(id, rubrica_id FK, version int, contenido jsonb, estado[borrador|aprobada], creada_por, creada_en)
entregas(id, estudiante_id FK, laboratorio_id FK, rubrica_version_id FK, pdf_path, codigo_zip_path, github_url, extras jsonb, creada_en)
evaluaciones(id, entrega_id FK, estado, nota numeric(2,1), proveedor, modelo, prompt_version, temperatura,
             respuesta_cruda jsonb, resultado jsonb, error text, creada_en, aprobada_por, aprobada_en, publicada_en)
evaluacion_criterios(id, evaluacion_id FK, criterio_id, nivel_ia, nivel_final, puntaje_normalizado, evidencias jsonb,
                     evidencias_verificadas jsonb, justificacion, ajuste_docente text)
verificaciones_codigo(id, evaluacion_id FK, sintaxis jsonb, ruff jsonb, complejidad jsonb, tests jsonb, metricas jsonb, sandbox text)
auditoria(id, usuario_id, entidad, entidad_id, accion, antes jsonb, despues jsonb, motivo, creado_en)
tematicas(id, nombre, padre_id NULL, descripcion)            -- taxonomía del mapa mental
config_ia(id=1, proveedor, modelo, temperatura, actualizado_por, actualizado_en)
```

## 11. Contrato de API (para trabajar en paralelo frontend/backend)

Prefijo `/api`. Autenticación: `Authorization: Bearer <JWT de Supabase>`. Errores: `{ "detail": "mensaje en español" }`. Documentación automática en `/docs` (FastAPI).

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | /api/salud | público | Estado del servicio |
| GET | /api/yo | todos | Perfil del usuario actual |
| GET/PATCH | /api/usuarios, /api/usuarios/{id}/rol | admin/docente | Gestión de usuarios |
| GET | /api/cohortes | todos | Cohortes con laboratorios |
| POST/PUT/DELETE | /api/laboratorios[/{id}] | docente | CRUD laboratorios |
| POST | /api/laboratorios/{id}/rubrica/extraer | docente | Sube archivo → `RubricaSchema` + inconsistencias |
| POST | /api/rubricas/validar | docente | Valida JSON de rúbrica → lista de inconsistencias |
| POST | /api/laboratorios/{id}/rubrica/versiones | docente | Guarda y aprueba nueva versión |
| GET | /api/laboratorios/{id}/rubrica | todos | Versión vigente |
| POST | /api/entregas | estudiante | multipart: laboratorio_id, pdf, zip? , github_url?, extras? |
| GET | /api/entregas?estudiante_id= | est(propias)/docente | Portafolio |
| POST | /api/entregas/{id}/evaluar | estudiante/docente | Lanza evaluación (202 + evaluacion_id) |
| GET | /api/evaluaciones/{id} | según estado/rol | Detalle (estudiante solo si `publicada`) |
| PATCH | /api/evaluaciones/{id}/criterios/{criterio_id} | docente | Ajuste {nivel_final, motivo} → recalcula nota |
| POST | /api/evaluaciones/{id}/aprobar · /publicar | docente | Cambios de estado |
| GET | /api/evaluaciones/{id}/traza | docente | Trazabilidad completa |
| GET | /api/estudiantes/{id}/informe | est(propio)/docente | Informe integral (JSON) |
| GET | /api/estudiantes/{id}/mapa | est(propio)/docente | Grafo {nodos, aristas} |
| GET/PUT | /api/config-ia · POST /api/config-ia/probar | docente | Configuración IA |

## 12. Casos de uso principales

1. **CU-01 Docente prepara un laboratorio:** crea laboratorio → sube rúbrica → IA la estructura → sistema muestra inconsistencias → docente corrige → aprueba versión.
2. **CU-02 Estudiante entrega y se autoevalúa:** entra a su portafolio → elige laboratorio → sube PDF + ZIP/GitHub → pulsa "Evaluar" → ve progreso → queda "pendiente de revisión docente".
3. **CU-03 Docente revisa (HITL):** abre evaluación en borrador → revisa evidencias y verificaciones → ajusta un criterio con motivo → nota se recalcula → aprueba → publica.
4. **CU-04 Estudiante consulta su aprendizaje:** ve evaluación publicada con retroalimentación → abre informe integral → descarga PDF → explora el mapa mental → descarga PNG.
5. **CU-05 Visitante/jurado conoce el proyecto:** abre la URL → ve abstract y equipo → inicia sesión con cuenta de demo.

## 13. Ciclo Human-in-the-Loop (resumen para la socialización)

```
Estudiante sube evidencias → Verificación técnica (objetiva) → IA propone niveles + evidencias (estructurado)
→ Backend valida esquema, verifica citas y CALCULA la nota → Docente revisa / ajusta con motivo / aprueba
→ Publicación al estudiante → Informe + mapa mental (solo con datos publicados) → Auditoría de todo el proceso
```

## 14. Plan de trabajo (12–17 nov)

| Día | Rol 1 IA (Laura) | Rol 2 Backend (Mariana) | Rol 3 Frontend (Daniela) | Rol 4 DevOps/Calidad (Luna) |
|---|---|---|---|---|
| Jue 12 | Probar API key de Gemini y reunir rúbricas/labs reales del curso | — | — | Repo GitHub, carpetas del kit, Supabase creado, `/init` |
| Vie 13 | `LLMProvider` + esquemas + prompt de rúbrica | FastAPI base, auth JWT, modelos/migraciones, semilla | Next.js base, login, layout, página equipo/abstract | CI (ruff, pytest, eslint, tsc), deploy esqueleto Vercel+Render |
| Sáb 14 | Prompt de evaluación + verificación de citas | Rúbricas (validador) + entregas + storage | Pantallas rúbricas y portafolio | Verificador estático + sandbox |
| Dom 15 | Mapeo a temáticas + narrativa informe | Evaluación (tarea de fondo), nota, HITL, auditoría | Evaluación + revisión docente | Pruebas de integración, revisión seguridad |
| Lun 16 | Ajuste de prompts con labs reales | Informe + grafo del mapa | Informe (gráficas + PDF) + mapa mental | Deploy final, datos demo, cuentas demo, video plan B |
| Mar 17 | Mañana: pruebas finales y ensayo · Tarde/noche: **socialización** | | | |

**Prioridad si falta tiempo** (de primero a último): RF-01, 02, 03, 04, 05, 07 → RF-11 → RF-08 → RF-09 → RF-06 tests en sandbox → RF-10 panel.

## 15. Definición de terminado (global)
- Las 7 funcionalidades obligatorias accesibles desde la URL pública.
- Nota calculada solo por backend, con tests que lo prueban.
- Salidas de IA validadas con Pydantic.
- Ejecución de código solo en sandbox.
- Trazabilidad visible para el docente.
- `docs/USO_IA.md` completo (herramientas, aportes, limitaciones, decisiones).
- README con arquitectura, cómo ejecutar, variables de entorno, costos y limitaciones.
