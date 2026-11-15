"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Info, Loader2 } from "lucide-react";
import { useSesion } from "@/components/proveedor-sesion";
import { Button } from "@/components/ui/button";
import { MODO_MOCK, MOTIVO_SESION_EXPIRADA, mensajeDeError, obtenerYo } from "@/lib/api";
import {
  destinoSeguro,
  rutaInicioPorRol,
  traducirErrorAuth,
  validarContrasena,
  validarEmail,
} from "@/lib/auth";
import { SESION_SIMULADA_PERMITIDA, guardarSesionMock } from "@/lib/sesion-mock";
import { obtenerSupabaseNavegador } from "@/lib/supabase/cliente";
import { MENSAJE_SUPABASE_NO_CONFIGURADO } from "@/lib/supabase/config";

type Modo = "login" | "registro";

interface Errores {
  nombre?: string;
  email?: string;
  contrasena?: string;
}

interface CampoProps {
  id: string;
  etiqueta: string;
  tipo: string;
  valor: string;
  autoComplete: string;
  error?: string;
  deshabilitado: boolean;
  alCambiar: (valor: string) => void;
}

function Campo({ id, etiqueta, tipo, valor, autoComplete, error, deshabilitado, alCambiar }: CampoProps) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
      </label>
      <input
        id={id}
        name={id}
        type={tipo}
        value={valor}
        autoComplete={autoComplete}
        disabled={deshabilitado}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(evento) => alCambiar(evento.target.value)}
        className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive disabled:opacity-50"
      />
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

export function FormularioAuth({ modo }: { modo: Modo }) {
  const router = useRouter();
  const parametros = useSearchParams();
  const { recargar } = useSesion();
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [errores, setErrores] = useState<Errores>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const supabase = obtenerSupabaseNavegador();
  const sesionSimulada = !supabase && MODO_MOCK && SESION_SIMULADA_PERMITIDA;
  const bloqueado = !supabase && !sesionSimulada;
  const esRegistro = modo === "registro";

  const validar = (): boolean => {
    const nuevos: Errores = {};
    if (esRegistro && nombre.trim() === "") nuevos.nombre = "Escribe tu nombre completo.";
    const errorEmail = validarEmail(email);
    if (errorEmail) nuevos.email = errorEmail;
    const errorContrasena = validarContrasena(contrasena);
    if (errorContrasena) nuevos.contrasena = errorContrasena;
    setErrores(nuevos);
    return Object.keys(nuevos).length === 0;
  };

  const entrar = async () => {
    const perfil = await obtenerYo();
    await recargar();
    router.replace(destinoSeguro(parametros.get("siguiente")) ?? rutaInicioPorRol(perfil.rol));
    router.refresh();
  };

  const enviar = async (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setErrorGeneral(null);
    setAviso(null);
    if (bloqueado || !validar()) return;
    setEnviando(true);
    try {
      const correo = email.trim();
      if (!supabase) {
        guardarSesionMock(correo);
        await entrar();
        return;
      }
      if (esRegistro) {
        const { data, error } = await supabase.auth.signUp({
          email: correo,
          password: contrasena,
          options: { data: { nombre: nombre.trim() } },
        });
        if (error) {
          setErrorGeneral(traducirErrorAuth(error));
          return;
        }
        if (!data.session) {
          setAviso("Cuenta creada. Revisa tu correo para confirmarla y luego inicia sesión.");
          return;
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email: correo, password: contrasena });
        if (error) {
          setErrorGeneral(traducirErrorAuth(error));
          return;
        }
      }
      await entrar();
    } catch (causa) {
      setErrorGeneral(mensajeDeError(causa));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-md px-4 py-12 sm:py-16">
      <h1 className="text-3xl font-bold tracking-tight">{esRegistro ? "Crear cuenta" : "Iniciar sesión"}</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        {esRegistro
          ? "Regístrate con tu correo. Tu cuenta inicia con el rol de estudiante."
          : "Ingresa con tu correo y contraseña."}
      </p>

      {bloqueado && (
        <div role="alert" className="mt-6 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
          {MENSAJE_SUPABASE_NO_CONFIGURADO}
        </div>
      )}

      {!esRegistro && parametros.get("motivo") === MOTIVO_SESION_EXPIRADA && (
        <p role="status" className="mt-6 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Tu sesión expiró o ya no es válida. Vuelve a iniciar sesión para continuar.
        </p>
      )}

      {sesionSimulada && (
        <div className="mt-6 flex gap-2 rounded-lg border bg-muted/40 p-4 text-sm">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>
            Modo de prueba: Supabase no está configurado y se usan datos simulados. Se crea una sesión
            simulada con cualquier contraseña. El rol depende del correo: si contiene “admin” serás admin, si
            contiene “docente” serás docente; en otro caso, estudiante.
          </p>
        </div>
      )}

      <form onSubmit={enviar} noValidate className="mt-6 space-y-4">
        {esRegistro && (
          <Campo
            id="nombre"
            etiqueta="Nombre completo"
            tipo="text"
            valor={nombre}
            autoComplete="name"
            error={errores.nombre}
            deshabilitado={enviando || bloqueado}
            alCambiar={setNombre}
          />
        )}
        <Campo
          id="email"
          etiqueta="Correo electrónico"
          tipo="email"
          valor={email}
          autoComplete="email"
          error={errores.email}
          deshabilitado={enviando || bloqueado}
          alCambiar={setEmail}
        />
        <Campo
          id="contrasena"
          etiqueta="Contraseña"
          tipo="password"
          valor={contrasena}
          autoComplete={esRegistro ? "new-password" : "current-password"}
          error={errores.contrasena}
          deshabilitado={enviando || bloqueado}
          alCambiar={setContrasena}
        />

        {errorGeneral && (
          <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            {errorGeneral}
          </p>
        )}
        {aviso && (
          <p role="status" className="rounded-lg border bg-muted/40 p-3 text-sm">
            {aviso}
          </p>
        )}

        <Button type="submit" size="lg" className="w-full" disabled={enviando || bloqueado}>
          {enviando && <Loader2 className="animate-spin" aria-hidden="true" />}
          {enviando ? "Procesando…" : esRegistro ? "Crear cuenta" : "Ingresar"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        {esRegistro ? "¿Ya tienes cuenta? " : "¿No tienes cuenta? "}
        <Link
          href={esRegistro ? "/login" : "/registro"}
          className="font-medium text-foreground underline underline-offset-4"
        >
          {esRegistro ? "Inicia sesión" : "Regístrate"}
        </Link>
      </p>
    </div>
  );
}
