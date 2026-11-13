"""Tests de los validadores de los esquemas del LLM."""

import pytest
from pydantic import ValidationError

from app.ia.schemas import (
    Criterio,
    EvaluacionCriterio,
    EvaluacionLLMSchema,
    Evidencia,
    InformeNarrativoSchema,
    MapeoTematicasSchema,
    RubricaSchema,
)


def _niveles(*puntajes: float) -> list[dict]:
    return [
        {"nombre": f"Nivel {i}", "puntaje": p, "descriptor": f"Descriptor {i}"}
        for i, p in enumerate(puntajes)
    ]


def _criterio(**cambios) -> dict:
    base = {
        "id": "c1",
        "competencia": "Programación",
        "nombre": "Calidad del código",
        "ponderacion": 50,
        "niveles": _niveles(5, 3, 1),
    }
    base.update(cambios)
    return base


def test_criterio_valido() -> None:
    criterio = Criterio(**_criterio())
    assert len(criterio.niveles) == 3


def test_criterio_con_un_nivel_valida() -> None:
    assert len(Criterio(**_criterio(niveles=_niveles(5))).niveles) == 1


def test_criterio_sin_niveles_valida() -> None:
    assert Criterio(**_criterio(niveles=[])).niveles == []


def test_criterio_con_puntajes_repetidos_valida() -> None:
    criterio = Criterio(**_criterio(niveles=_niveles(5, 5)))
    assert [n.puntaje for n in criterio.niveles] == [5, 5]


def test_criterio_con_nombres_repetidos_valida() -> None:
    niveles = [
        {"nombre": "Alto", "puntaje": 5, "descriptor": "a"},
        {"nombre": "alto", "puntaje": 3, "descriptor": "b"},
    ]
    assert len(Criterio(**_criterio(niveles=niveles)).niveles) == 2


@pytest.mark.parametrize("ponderacion", [-1, 101])
def test_ponderacion_fuera_de_rango_falla(ponderacion: float) -> None:
    with pytest.raises(ValidationError):
        Criterio(**_criterio(ponderacion=ponderacion))


def test_rubrica_con_suma_distinta_de_100_no_se_rechaza() -> None:
    rubrica = RubricaSchema(titulo="Lab 1", criterios=[_criterio(ponderacion=30)])
    assert sum(c.ponderacion for c in rubrica.criterios) == 30


def _evaluacion_criterio(**cambios) -> dict:
    base = {
        "criterio_id": "c1",
        "nivel_elegido": "Nivel 0",
        "evidencias": [{"fragmento": "def suma(a, b):", "fuente": "codigo"}],
        "justificacion": "Código claro.",
        "fortalezas": ["Nombres descriptivos"],
        "debilidades": [],
        "recomendacion": "Agregar pruebas.",
    }
    base.update(cambios)
    return base


def test_evaluacion_sin_evidencias_falla() -> None:
    with pytest.raises(ValidationError):
        EvaluacionCriterio(**_evaluacion_criterio(evidencias=[]))


def test_evidencia_con_fragmento_vacio_falla() -> None:
    with pytest.raises(ValidationError, match="vacío"):
        Evidencia(fragmento="   ", fuente="informe")


def test_evidencia_ubicacion_opcional() -> None:
    assert Evidencia(fragmento="texto", fuente="informe").ubicacion is None


def test_evaluacion_llm_no_tiene_campo_nota() -> None:
    assert "nota" not in EvaluacionLLMSchema.model_fields
    assert "nota" not in EvaluacionCriterio.model_fields
    evaluacion = EvaluacionLLMSchema(
        criterios=[EvaluacionCriterio(**_evaluacion_criterio())],
        aprendizajes_identificados=["Funciones"],
        como_aplico_conocimientos="Aplicó funciones puras.",
        aspectos_a_fortalecer=["Pruebas"],
        retroalimentacion_general="Buen trabajo.",
    )
    assert "nota" not in evaluacion.model_dump()


def test_informe_prioridad_invalida_falla() -> None:
    with pytest.raises(ValidationError):
        InformeNarrativoSchema(
            competencias_desarrolladas=[],
            brechas=[],
            plan_fortalecimiento=[
                {"accion": "a", "recurso": "r", "prioridad": "urgente", "competencia": "c"}
            ],
            conclusion="",
        )


def test_mapeo_tematicas_valido() -> None:
    mapeo = MapeoTematicasSchema(
        mapeos=[{"criterio_id": "c1", "tematicas": ["POO"], "conceptos": ["clase"]}]
    )
    assert mapeo.mapeos[0].tematicas == ["POO"]
