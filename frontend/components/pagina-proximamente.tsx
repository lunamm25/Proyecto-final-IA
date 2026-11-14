import { GuardaRol } from "@/components/guarda-rol";
import type { Rol } from "@/lib/tipos";

interface PaginaProximamenteProps {
  titulo: string;
  descripcion: string;
  roles: Rol[];
}

export function PaginaProximamente({ titulo, descripcion, roles }: PaginaProximamenteProps) {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-12">
      <GuardaRol roles={roles}>
        <h1 className="text-3xl font-bold tracking-tight">{titulo}</h1>
        <p className="mt-2 text-muted-foreground">{descripcion}</p>
        <div className="mt-8 rounded-xl border border-dashed p-8 text-center text-muted-foreground">
          Próximamente
        </div>
      </GuardaRol>
    </div>
  );
}
