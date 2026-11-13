"""Carga los datos semilla (cohortes, laboratorios, temáticas, config_ia).

Uso, desde la carpeta backend/ con el entorno virtual activado:
    python seed.py
Es idempotente: si se corre dos veces no duplica datos.
"""

import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import seed_datos
from app.config import get_settings
from app.db import SessionLocal
from app.models import Cohorte, ConfigIA, Laboratorio, Tematica


def _sembrar_cohortes(session: Session) -> dict[int, Cohorte]:
    """Crea las cohortes que falten y devuelve un dict numero -> Cohorte."""
    cohortes: dict[int, Cohorte] = {}
    for datos in seed_datos.COHORTES:
        cohorte = session.scalar(select(Cohorte).where(Cohorte.numero == datos["numero"]))
        if cohorte is None:
            cohorte = Cohorte(numero=datos["numero"], nombre=datos["nombre"])
            session.add(cohorte)
            session.flush()
        cohortes[cohorte.numero] = cohorte
    return cohortes


def _sembrar_laboratorios(session: Session, cohortes: dict[int, Cohorte]) -> None:
    """Crea los laboratorios que falten (por código), sin sobrescribir existentes."""
    for datos in seed_datos.LABORATORIOS:
        existe = session.scalar(select(Laboratorio.id).where(Laboratorio.codigo == datos["codigo"]))
        if existe is not None:
            continue
        session.add(
            Laboratorio(
                cohorte_id=cohortes[datos["cohorte"]].id,
                codigo=datos["codigo"],
                titulo=datos["titulo"],
                descripcion=datos.get("descripcion"),
                objetivos=datos.get("objetivos"),
            )
        )


def _sembrar_tematicas(session: Session) -> None:
    """Crea las temáticas base que falten (por nombre)."""
    for datos in seed_datos.TEMATICAS:
        existe = session.scalar(select(Tematica.id).where(Tematica.nombre == datos["nombre"]))
        if existe is None:
            session.add(Tematica(nombre=datos["nombre"], descripcion=datos.get("descripcion")))


def _sembrar_config_ia(session: Session) -> None:
    """Crea la fila única de config_ia (id = 1) si no existe."""
    if session.get(ConfigIA, 1) is None:
        session.add(ConfigIA(id=1, **seed_datos.CONFIG_IA))


def sembrar(session: Session) -> None:
    """Inserta todos los datos semilla de forma idempotente y confirma la transacción."""
    cohortes = _sembrar_cohortes(session)
    _sembrar_laboratorios(session, cohortes)
    _sembrar_tematicas(session)
    _sembrar_config_ia(session)
    session.commit()


def main() -> int:
    """Punto de entrada por consola; devuelve el código de salida."""
    if not get_settings().database_url.strip():
        print("Error: falta DATABASE_URL en backend/.env. Cópiala desde el panel de Supabase.")
        return 1
    try:
        with SessionLocal() as session:
            sembrar(session)
    except SQLAlchemyError as error:
        print("Error: no se pudo conectar o escribir en la base de datos.")
        print(f"Detalle: {type(error).__name__}: {str(error).splitlines()[0]}")
        print("Revisa DATABASE_URL y que la migración 0001_esquema_inicial.sql esté aplicada.")
        return 1
    print("Datos semilla cargados correctamente (cohortes, laboratorios, temáticas, config_ia).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
