"""Pruebas del esquema: tablas, columnas clave y restricciones (SQLite en memoria)."""

import uuid

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.models import Cohorte, ConfigIA, Evaluacion, Laboratorio, Perfil, Rubrica, RubricaVersion

TABLAS_Y_COLUMNAS = {
    "perfiles": {"id", "nombre", "rol", "foto_url", "creado_en"},
    "cohortes": {"id", "nombre", "numero"},
    "laboratorios": {"id", "cohorte_id", "codigo", "titulo", "descripcion", "objetivos"},
    "rubricas": {"id", "laboratorio_id"},
    "rubrica_versiones": {
        "id", "rubrica_id", "version", "contenido", "estado", "creada_por", "creada_en",
    },
    "entregas": {
        "id", "estudiante_id", "laboratorio_id", "rubrica_version_id", "pdf_path",
        "codigo_zip_path", "github_url", "extras", "creada_en",
    },
    "evaluaciones": {
        "id", "entrega_id", "estado", "nota", "proveedor", "modelo", "prompt_version",
        "temperatura", "respuesta_cruda", "resultado", "error", "creada_en", "aprobada_por",
        "aprobada_en", "publicada_en",
    },
    "evaluacion_criterios": {
        "id", "evaluacion_id", "criterio_id", "nivel_ia", "nivel_final", "puntaje_normalizado",
        "evidencias", "evidencias_verificadas", "justificacion", "ajuste_docente",
    },
    "verificaciones_codigo": {
        "id", "evaluacion_id", "sintaxis", "ruff", "complejidad", "tests", "metricas", "sandbox",
    },
    "auditoria": {
        "id", "usuario_id", "entidad", "entidad_id", "accion", "antes", "despues", "motivo",
        "creado_en",
    },
    "tematicas": {"id", "nombre", "padre_id", "descripcion"},
    "config_ia": {
        "id", "proveedor", "modelo", "temperatura", "actualizado_por", "actualizado_en",
    },
}


def _laboratorio(sesion, codigo: str = "L1") -> Laboratorio:
    """Crea una cohorte y un laboratorio de prueba."""
    cohorte = Cohorte(numero=99, nombre="Cohorte prueba")
    sesion.add(cohorte)
    sesion.flush()
    lab = Laboratorio(cohorte_id=cohorte.id, codigo=codigo, titulo="Lab de prueba")
    sesion.add(lab)
    sesion.flush()
    return lab


def test_crea_todas_las_tablas_con_columnas_clave(engine_sqlite):
    inspector = inspect(engine_sqlite)
    assert set(inspector.get_table_names()) == set(TABLAS_Y_COLUMNAS)
    for tabla, columnas in TABLAS_Y_COLUMNAS.items():
        reales = {c["name"] for c in inspector.get_columns(tabla)}
        assert columnas <= reales, f"Faltan columnas en {tabla}: {columnas - reales}"


def test_rol_por_defecto_es_estudiante(sesion):
    perfil = Perfil(id=uuid.uuid4(), nombre="Ana")
    sesion.add(perfil)
    sesion.commit()
    sesion.refresh(perfil)
    assert perfil.rol == "estudiante"


def test_rol_invalido_es_rechazado(sesion):
    sesion.add(Perfil(id=uuid.uuid4(), nombre="X", rol="superusuario"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_una_sola_rubrica_por_laboratorio(sesion):
    lab = _laboratorio(sesion)
    sesion.add(Rubrica(laboratorio_id=lab.id))
    sesion.commit()
    sesion.add(Rubrica(laboratorio_id=lab.id))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_version_de_rubrica_unica(sesion):
    lab = _laboratorio(sesion)
    rubrica = Rubrica(laboratorio_id=lab.id)
    sesion.add(rubrica)
    sesion.flush()
    sesion.add(RubricaVersion(rubrica_id=rubrica.id, version=1, contenido={"titulo": "R"}))
    sesion.commit()
    sesion.add(RubricaVersion(rubrica_id=rubrica.id, version=1, contenido={"titulo": "R2"}))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_rubrica_version_estado_por_defecto_borrador(sesion):
    lab = _laboratorio(sesion)
    rubrica = Rubrica(laboratorio_id=lab.id)
    sesion.add(rubrica)
    sesion.flush()
    version = RubricaVersion(rubrica_id=rubrica.id, version=1, contenido={"criterios": []})
    sesion.add(version)
    sesion.commit()
    assert version.estado == "borrador"
    assert version.contenido == {"criterios": []}


def test_estado_de_evaluacion_invalido_es_rechazado(sesion):
    sesion.add(Evaluacion(entrega_id=1, estado="inventado"))
    with pytest.raises(IntegrityError, match="CHECK constraint"):
        sesion.commit()


def test_config_ia_solo_admite_id_1(sesion):
    sesion.add(ConfigIA(id=2, proveedor="gemini", modelo="m", temperatura=0.1))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_config_ia_rechaza_temperatura_alta(sesion):
    sesion.add(ConfigIA(id=1, proveedor="gemini", modelo="m", temperatura=0.9))
    with pytest.raises(IntegrityError):
        sesion.commit()
