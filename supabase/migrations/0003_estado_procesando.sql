-- =====================================================================
-- 0003 · Estado "procesando" en evaluaciones (RF-05)
-- Mientras la IA evalúa en segundo plano, la evaluación queda en
-- 'procesando'; al terminar pasa a 'borrador' o 'error'.
-- El índice único parcial impide que una misma entrega tenga dos
-- evaluaciones en curso a la vez (doble clic o peticiones simultáneas).
-- Idempotente: se puede ejecutar varias veces sin error.
-- =====================================================================

alter table public.evaluaciones drop constraint if exists evaluaciones_estado_check;
alter table public.evaluaciones
    add constraint evaluaciones_estado_check
    check (estado in ('procesando', 'borrador', 'en_revision', 'aprobada', 'publicada', 'error'));

create unique index if not exists ux_evaluaciones_entrega_procesando
    on public.evaluaciones (entrega_id)
    where estado = 'procesando';
