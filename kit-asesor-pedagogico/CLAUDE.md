# CLAUDE.md — Asesor Pedagógico Inteligente

Reglas permanentes para Claude Code en este repositorio. Léelas completas al iniciar cada sesión.

## 1. Contexto
- Documento maestro: `docs/REQUISITOS.md`. Es la fuente única de verdad: requisitos (RF/RNF), esquemas, contrato de API, modelo de datos y plan. **No inventes funcionalidades fuera de él.** Si algo no está claro, pregunta.
- Nivel acordado: **FUNCIONAL Y SÓLIDO**. Cumplir los requisitos sin sobreingeniería. Antes de agregar algo "más avanzado" (nueva librería, nuevo servicio, patrón complejo), **pregunta primero**.
- Equipo: 4 integrantes con poca experiencia técnica. Explica en español, paso a paso, y dile a la persona qué comando correr y qué debería ver.
- Entrega: martes 17 nov 2026. El tiempo y los tokens son limitados.

## 2. Estructura del repositorio
```
frontend/            Next.js + TS + Tailwind + shadcn/ui        (Rol 3)
backend/app/api/     Rutas FastAPI                               (Rol 2)
backend/app/models/  SQLAlchemy                                  (Rol 2)
backend/app/services/ Lógica de negocio (nota, HITL, informe)    (Rol 2)
backend/app/ia/      LLMProvider, prompts, schemas, evaluador    (Rol 1)
backend/app/verificacion/ Estático + sandbox                     (Rol 4)
backend/tests/       Pytest
supabase/migrations/ SQL
docs/                REQUISITOS.md, USO_IA.md, ARQUITECTURA.md
.github/workflows/   CI
```
Cada rol trabaja **solo en su carpeta**. Si necesitas cambiar la carpeta de otro rol, avisa y explica por qué.

## 3. Regla de oro: nada entra sin verificarse
Después de **cada cambio** (no al final del día):
1. **Backend:** `cd backend && ruff check . && pytest -q`
2. **Frontend:** `cd frontend && npm run lint && npx tsc --noEmit && npm run build`
3. Prueba manual mínima del flujo tocado (endpoint en `/docs` o pantalla en el navegador).
4. Si algo falla, **corrígelo antes de seguir**. Nunca digas "listo" con pruebas rojas o sin haber ejecutado nada.
5. Reporta al final de cada tarea: qué cambiaste, qué comandos corriste y su resultado, y qué falta.

Se usa `/verificar` (en `.claude/commands/`) para correr todo junto.

## 4. Metodología de trabajo
- **Incremental:** una tarea pequeña a la vez (un endpoint, una pantalla, una función). Plan corto → implementar → verificar → commit.
- **Tests primero en lo crítico:** cálculo de nota, validador de rúbricas, permisos por rol, verificación de citas, límites de ZIP. El resto, con tests básicos.
- **Commits pequeños** con Conventional Commits en español: `feat(frontend): pantalla de portafolio`, `fix(backend): ...`, `test: ...`.
- **Ramas:** `main` (siempre desplegable) y una rama por rol: `rol1-ia`, `rol2-backend`, `rol3-frontend`, `rol4-devops`. Integrar a `main` con PR cuando la tarea está verificada.
- **Contrato primero:** frontend y backend se guían por la tabla de API de `docs/REQUISITOS.md` §11. Si cambia un endpoint, actualiza esa tabla en el mismo commit.
- Al terminar un RF, márcalo en `docs/PROGRESO.md` (créalo si no existe) con fecha y quién lo verificó.

## 5. Reglas de oro del dominio (se evalúan)
- La **nota 0,0–5,0 la calcula el backend** (`backend/app/services/nota.py`). El LLM nunca calcula ni devuelve la nota.
- Toda salida del LLM se valida con **Pydantic** (`backend/app/ia/schemas.py`). Si no valida: reintentar hasta 2 veces y luego estado `error`.
- `temperature ≤ 0.2`. Prompts en archivos versionados (`backend/app/ia/prompts/*.md` con `version:`).
- Código del estudiante = no confiable. **Nunca** se ejecuta fuera de `SandboxRunner`. El análisis estático no ejecuta código.
- Cada evaluación guarda proveedor, modelo, versión de prompt, versión de rúbrica, respuesta cruda, verificaciones y ajustes (trazabilidad).
- El estudiante solo ve evaluaciones `publicada`. Los ajustes del docente exigen motivo y quedan en `auditoria`.

## 6. Seguridad
- Secretos solo en `.env` (nunca en el código ni en commits). Mantén `.env.example` actualizado.
- Backend valida el JWT de Supabase en cada ruta protegida y aplica rol.
- Bucket privado + URLs firmadas. Validar tamaño y tipo de cada archivo.
- CORS solo para el dominio del frontend y `localhost:3000`.

## 7. Estilo
- Interfaz y mensajes al usuario en **español**. Nombres de código: español para dominio (`rubrica`, `entrega`), inglés aceptado para términos técnicos.
- Python: type hints, funciones cortas, docstring de una línea. TypeScript estricto, sin `any`.
- UI: shadcn/ui + Tailwind; cada pantalla con estado de carga, vacío y error.

## 8. Uso de tokens y sesiones (importante)
- No leas todo el repo en cada tarea: lee `CLAUDE.md`, la sección relevante de `REQUISITOS.md` y solo los archivos que vas a tocar.
- Usa subagentes solo cuando la tarea lo amerita (ver `.claude/agents/`). No lances varios agentes a la vez para tareas pequeñas.
- Cada integrante trabaja con **su propia cuenta** en su rol: así se reparte el límite de las ventanas de 5 horas.
- Antes de que se acabe la sesión, deja anotado en `docs/PROGRESO.md` dónde quedaste y el siguiente paso.

## 9. Qué NO hacer
- No agregar microservicios, Redis, Celery, Kubernetes ni otra base de datos. Para tareas de fondo usa `BackgroundTasks` de FastAPI.
- No cambiar el stack sin preguntar.
- No borrar ni reescribir el trabajo de otro rol.
- No dejar `console.log`/`print` de depuración, claves de prueba ni código comentado.
- No marcar nada como terminado sin la verificación de la sección 3.
