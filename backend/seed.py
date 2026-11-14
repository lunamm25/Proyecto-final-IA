"""Carga los datos semilla (cohortes, laboratorios con su rúbrica, temáticas, config_ia).

Uso, desde la carpeta backend/ con el entorno virtual activado:
    python seed.py
Es idempotente: si se corre dos veces no duplica datos y no toca rúbricas que ya
tengan versiones (respeta los cambios del docente).
"""

import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import seed_datos
from app.config import get_settings
from app.db import SessionLocal
from app.models import Cohorte, ConfigIA, Laboratorio, Rubrica, RubricaVersion, Tematica
from app.services.rubricas import validar_rubrica

CARPETA_RUBRICAS = Path(__file__).resolve().parent / "rubricas_demo"


class SemillaInvalidaError(Exception):
    """Un archivo de rúbrica de demo falta, no es JSON o tiene inconsistencias."""


def _cargar_rubrica(archivo: str) -> dict[str, Any]:
    """Lee y valida una rúbrica de `rubricas_demo/`; lanza SemillaInvalidaError si falla."""
    ruta = CARPETA_RUBRICAS / archivo
    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SemillaInvalidaError(f"No se encontró el archivo de rúbrica {ruta}.") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SemillaInvalidaError(
            f"El archivo de rúbrica {archivo} no es un JSON válido: {error}."
        ) from None
    inconsistencias = validar_rubrica(contenido)
    if inconsistencias:
        detalle = "\n".join(f"  - {texto}" for texto in inconsistencias)
        raise SemillaInvalidaError(f"La rúbrica {archivo} tiene inconsistencias:\n{detalle}")
    return contenido


def _cargar_rubricas() -> dict[str, dict[str, Any]]:
    """Lee y valida todas las rúbricas de demo antes de escribir en la base de datos."""
    return {
        datos["codigo"]: _cargar_rubrica(datos["rubrica_archivo"])
        for datos in seed_datos.LABORATORIOS
        if datos.get("rubrica_archivo")
    }


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


def _sembrar_laboratorios(session: Session, cohortes: dict[int, Cohorte]) -> dict[str, Laboratorio]:
    """Crea los laboratorios que falten (por código), sin sobrescribir existentes."""
    laboratorios: dict[str, Laboratorio] = {}
    for datos in seed_datos.LABORATORIOS:
        laboratorio = session.scalar(
            select(Laboratorio).where(Laboratorio.codigo == datos["codigo"])
        )
        if laboratorio is None:
            laboratorio = Laboratorio(
                cohorte_id=cohortes[datos["cohorte"]].id,
                codigo=datos["codigo"],
                titulo=datos["titulo"],
                descripcion=datos.get("descripcion"),
                objetivos=datos.get("objetivos"),
            )
            session.add(laboratorio)
            session.flush()
        laboratorios[laboratorio.codigo] = laboratorio
    return laboratorios


def _sembrar_rubrica(session: Session, laboratorio: Laboratorio, contenido: dict) -> None:
    """Crea la versión 1 aprobada si el laboratorio aún no tiene ninguna versión."""
    rubrica = session.scalar(select(Rubrica).where(Rubrica.laboratorio_id == laboratorio.id))
    if rubrica is None:
        rubrica = Rubrica(laboratorio_id=laboratorio.id)
        session.add(rubrica)
        session.flush()
    tiene_versiones = session.scalar(
        select(RubricaVersion.id).where(RubricaVersion.rubrica_id == rubrica.id).limit(1)
    )
    if tiene_versiones is None:
        session.add(
            RubricaVersion(
                rubrica_id=rubrica.id,
                version=1,
                estado="aprobada",
                contenido=contenido,
                creada_por=None,
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
    rubricas = _cargar_rubricas()
    cohortes = _sembrar_cohortes(session)
    laboratorios = _sembrar_laboratorios(session, cohortes)
    for codigo, contenido in rubricas.items():
        _sembrar_rubrica(session, laboratorios[codigo], contenido)
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
    except SemillaInvalidaError as error:
        print(f"Error: no se cargó ningún dato. {error}")
        print("Corrige el archivo en backend/rubricas_demo/ y vuelve a correr el seed.")
        return 1
    except SQLAlchemyError as error:
        print("Error: no se pudo conectar o escribir en la base de datos.")
        print(f"Detalle: {type(error).__name__}: {str(error).splitlines()[0]}")
        print("Revisa DATABASE_URL y que la migración 0001_esquema_inicial.sql esté aplicada.")
        return 1
    print(
        "Datos semilla cargados correctamente "
        "(cohortes, laboratorios, rúbricas, temáticas, config_ia)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
