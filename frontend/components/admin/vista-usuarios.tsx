"use client";

import { useState } from "react";
import { Cargando, EstadoVacio, MensajeError } from "@/components/estados";
import { CambioRol } from "@/components/admin/cambio-rol";
import {
  ROLES,
  TEXTO_ROL,
  esFiltroRol,
  filtrarUsuarios,
  type FiltroRol,
} from "@/components/admin/reglas-usuarios";
import { useSesion } from "@/components/proveedor-sesion";
import { listarUsuarios } from "@/lib/api";
import { nombreVisible } from "@/lib/perfil";
import type { Perfil, Usuario } from "@/lib/tipos";
import { useCarga } from "@/lib/use-carga";

const SIN_CORREO = "Sin correo registrado";

interface FiltrosProps {
  busqueda: string;
  filtro: FiltroRol;
  alBuscar: (texto: string) => void;
  alFiltrar: (filtro: FiltroRol) => void;
}

function Filtros({ busqueda, filtro, alBuscar, alFiltrar }: FiltrosProps) {
  return (
    <div role="search" className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex-1 space-y-1">
        <label htmlFor="buscar-usuario" className="text-sm font-medium">Buscar por nombre o correo</label>
        <input id="buscar-usuario" type="search" value={busqueda} onChange={(e) => alBuscar(e.target.value)}
          className="h-9 w-full rounded-lg border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50" />
      </div>
      <div className="space-y-1">
        <label htmlFor="filtro-rol" className="text-sm font-medium">Rol</label>
        <select id="filtro-rol" value={filtro}
          onChange={(e) => { if (esFiltroRol(e.target.value)) alFiltrar(e.target.value); }}
          className="h-9 w-full rounded-lg border bg-background px-3 text-sm sm:w-48">
          <option value="todos">Todos</option>
          {ROLES.map((rol) => <option key={rol} value={rol}>{TEXTO_ROL[rol]}</option>)}
        </select>
      </div>
    </div>
  );
}

interface ListaProps {
  usuarios: Usuario[];
  actual: Perfil;
  alActualizar: (usuario: Usuario) => void;
}

function TablaUsuarios({ usuarios, actual, alActualizar }: ListaProps) {
  return (
    <div className="hidden overflow-x-auto rounded-xl border md:block">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Usuarios registrados y su rol</caption>
        <thead className="bg-muted/60 text-xs uppercase text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3">Nombre</th>
            <th scope="col" className="px-4 py-3">Correo</th>
            <th scope="col" className="px-4 py-3">Rol</th>
          </tr>
        </thead>
        <tbody>
          {usuarios.map((usuario) => (
            <tr key={usuario.id} className="border-t align-top">
              <td className="px-4 py-3 font-medium">{nombreVisible(usuario.nombre)}</td>
              <td className="px-4 py-3 break-all">{usuario.correo ?? SIN_CORREO}</td>
              <td className="px-4 py-3">
                <CambioRol usuario={usuario} actual={actual} idBase="tabla" alActualizar={alActualizar} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TarjetasUsuarios({ usuarios, actual, alActualizar }: ListaProps) {
  return (
    <ul className="space-y-3 md:hidden">
      {usuarios.map((usuario) => (
        <li key={usuario.id} className="rounded-xl border bg-card p-4">
          <p className="font-semibold">{nombreVisible(usuario.nombre)}</p>
          <p className="mb-3 text-sm break-all">{usuario.correo ?? SIN_CORREO}</p>
          <CambioRol usuario={usuario} actual={actual} idBase="tarjeta" alActualizar={alActualizar} />
        </li>
      ))}
    </ul>
  );
}

function ListaUsuarios({ usuarios, actual }: { usuarios: Usuario[]; actual: Perfil }) {
  const [actualizados, setActualizados] = useState<Record<string, Usuario>>({});
  const [busqueda, setBusqueda] = useState("");
  const [filtro, setFiltro] = useState<FiltroRol>("todos");
  const todos = usuarios.map((usuario) => actualizados[usuario.id] ?? usuario);
  const visibles = filtrarUsuarios(todos, busqueda, filtro);
  const alActualizar = (usuario: Usuario) => setActualizados((previo) => ({ ...previo, [usuario.id]: usuario }));

  if (usuarios.length === 0) {
    return <EstadoVacio titulo="No hay usuarios" mensaje="Cuando alguien se registre aparecerá aquí." />;
  }
  return (
    <div className="mt-8 space-y-4">
      <Filtros busqueda={busqueda} filtro={filtro} alBuscar={setBusqueda} alFiltrar={setFiltro} />
      <p aria-live="polite" className="text-sm text-muted-foreground">
        Mostrando {visibles.length} de {todos.length} usuarios.
      </p>
      {visibles.length === 0 ? (
        <EstadoVacio titulo="Ningún usuario coincide con la búsqueda" mensaje="Prueba con otro nombre, correo o rol." />
      ) : (
        <>
          <TablaUsuarios usuarios={visibles} actual={actual} alActualizar={alActualizar} />
          <TarjetasUsuarios usuarios={visibles} actual={actual} alActualizar={alActualizar} />
        </>
      )}
    </div>
  );
}

/** Pantalla de RF-01 CA3: lista de usuarios y cambio de rol. */
export function VistaUsuarios() {
  const { estado, recargar } = useCarga(listarUsuarios);
  const { perfil } = useSesion();

  if (estado.tipo === "cargando" || !perfil) return <Cargando texto="Cargando usuarios…" />;
  if (estado.tipo === "error") {
    return <MensajeError titulo="No se pudo cargar la lista de usuarios" mensaje={estado.mensaje} alReintentar={recargar} />;
  }
  return <ListaUsuarios usuarios={estado.datos} actual={perfil} />;
}
