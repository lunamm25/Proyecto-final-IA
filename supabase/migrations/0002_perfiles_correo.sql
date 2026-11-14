-- =====================================================================
-- 0002 · Correo en perfiles (RF-01 CA3: el admin ve id, nombre, correo y rol)
-- El correo vive en auth.users; se copia a public.perfiles para que el
-- backend lo lea sin consultar el esquema auth. Idempotente: se puede
-- ejecutar varias veces sin error.
-- =====================================================================

alter table public.perfiles add column if not exists correo text;

-- Rellena el correo de los perfiles que ya existían.
update public.perfiles p
set correo = u.email
from auth.users u
where u.id = p.id
  and p.correo is null;

-- Trigger RF-01 CA2 actualizado: además guarda el correo y limita el
-- nombre a 120 caracteres. El rol sigue siendo SIEMPRE 'estudiante'.
create or replace function public.crear_perfil_nuevo_usuario()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.perfiles (id, nombre, correo, rol)
    values (
        new.id,
        left(coalesce(new.raw_user_meta_data ->> 'nombre', new.email), 120),
        new.email,
        'estudiante'
    )
    on conflict (id) do nothing;
    return new;
end;
$$;

-- La función solo la usa el trigger: nadie más debe poder ejecutarla.
revoke execute on function public.crear_perfil_nuevo_usuario() from public, anon, authenticated;
