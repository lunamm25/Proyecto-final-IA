# Progreso del proyecto

| RF | Descripción | Responsable | Estado | Verificado por / fecha |
|---|---|---|---|---|
| RF-01 | Autenticación y usuarios | Rol 2 + Rol 3 | En progreso (backend listo: CA2, CA3, CA4; falta frontend) | |
| RF-02 | Cohortes y laboratorios | Rol 2 | En progreso | |
| RF-03 | Gestión de rúbricas | Rol 1 + 2 + 3 | Pendiente | |
| RF-04 | Portafolio académico | Rol 2 + 3 | Pendiente | |
| RF-05 | Evaluación inteligente | Rol 1 + 2 + 3 | Pendiente | |
| RF-06 | Verificación de código / sandbox | Rol 4 | Pendiente | |
| RF-07 | Revisión docente (HITL) | Rol 2 + 3 | Pendiente | |
| RF-08 | Informe integral | Rol 1 + 2 + 3 | Pendiente | |
| RF-09 | Mapa mental | Rol 1 + 2 + 3 | Pendiente | |
| RF-10 | Configuración de IA | Rol 1 + 3 | Pendiente | |
| RF-11 | Proyecto y equipo | Rol 3 | Pendiente | |
| Deploy | URL pública + datos demo | Rol 4 | Pendiente | |

## Bitácora de sesiones
<!-- Formato: fecha · integrante · qué se hizo · siguiente paso -->
- 2026-11-13 · Mariana (Rol 2) · Se cargaron en el seed los 4 laboratorios de demo (C1-01 Parcial 1 Fundamentos de IA, C1-02 Manizales Resiliente, C2-01 Laboratorio 01 Automatización de archivos, C2-02 Laboratorio 03 Agente con Ollama) con sus rúbricas de `backend/rubricas_demo/` como versión 1 aprobada (validadas con `validar_rubrica` y `calcular_nota`); se borraron de Supabase los 6 laboratorios `[PROVISIONAL]` (sin entregas) · Siguiente paso: correr `python seed.py` contra Supabase y revisar `GET /api/cohortes` y la rúbrica vigente de cada laboratorio en `/docs`.

> **Nota:** Las ponderaciones de LAB03 y los niveles de desempeño de LAB01 y Manizales Resiliente son propuestas del equipo, pendientes de aprobación docente.

- 2026-11-14 · Mariana (Rol 2) · Gestión de usuarios y roles (RF-01 CA3): `GET /api/usuarios` y `PATCH /api/usuarios/{id}/rol`, **solo admin** (decisión del equipo; REQUISITOS §11 y RF-01 CA3 actualizados, antes decían admin/docente). 409 si un admin se quita su propio rol de admin o si se dejaría el sistema sin admin; mismo rol → 200 sin auditoría; cada cambio queda en `auditoria`. Migración `0002_perfiles_correo.sql` (columna `correo` en `perfiles`). 256 tests en verde · Siguiente paso: aplicar la 0002 en Supabase (obligatorio antes de usar esta versión del backend) y nombrar al primer admin.
