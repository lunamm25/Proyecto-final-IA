-- 0006: el PDF del informe pasa a ser opcional en las entregas.
-- Decisión del equipo (14 nov 2026): una entrega necesita al menos uno de PDF, ZIP o URL de
-- GitHub (lo valida el backend). Si se adjunta un PDF, debe tener texto extraíble.
-- Idempotente: se puede ejecutar varias veces.
alter table public.entregas alter column pdf_path drop not null;
