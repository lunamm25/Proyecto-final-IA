-- =====================================================================
-- 0004 · Retroalimentación editada por el docente (RF-07 CA2)
-- El docente puede editar la retroalimentación sin borrar el texto
-- original de la IA (trazabilidad):
--   evaluaciones.retroalimentacion_docente: textos generales editados
--     (retroalimentacion_general, como_aplico_conocimientos,
--      aprendizajes_identificados, aspectos_a_fortalecer).
--   evaluacion_criterios.retroalimentacion_docente: textos editados del
--     criterio (justificacion, fortalezas, debilidades, recomendacion).
-- Solo se guardan las claves editadas; lo demás sigue siendo de la IA
-- (columnas resultado y justificacion, que no se modifican).
-- Idempotente: se puede ejecutar varias veces sin error.
-- =====================================================================

alter table public.evaluaciones
    add column if not exists retroalimentacion_docente jsonb;

alter table public.evaluacion_criterios
    add column if not exists retroalimentacion_docente jsonb;
