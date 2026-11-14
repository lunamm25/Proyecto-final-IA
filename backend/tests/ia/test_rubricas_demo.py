"""Tests de las rúbricas de demostración en formato RubricaSchema (sin llamadas a la IA)."""

from pathlib import Path

import pytest

from app.ia.schemas import RubricaSchema

CARPETA_DEMO = Path(__file__).parent / "fixtures" / "rubricas_demo"
ARCHIVOS_DEMO = [ruta.name for ruta in sorted(CARPETA_DEMO.glob("rubrica_*.json"))]


def _cargar(nombre: str) -> RubricaSchema:
    """Lee y valida una rúbrica de demostración con RubricaSchema."""
    contenido = (CARPETA_DEMO / nombre).read_text(encoding="utf-8")
    return RubricaSchema.model_validate_json(contenido)


@pytest.mark.parametrize("nombre", ARCHIVOS_DEMO)
def test_rubrica_demo_valida_con_el_esquema(nombre: str) -> None:
    """Cada JSON de demostración valida como RubricaSchema y tiene criterios."""
    rubrica = _cargar(nombre)
    assert rubrica.criterios


@pytest.mark.parametrize("nombre", ARCHIVOS_DEMO)
def test_rubrica_demo_ponderaciones_suman_100(nombre: str) -> None:
    """Las ponderaciones de cada rúbrica de demostración suman 100."""
    rubrica = _cargar(nombre)
    suma = sum(criterio.ponderacion for criterio in rubrica.criterios)
    assert suma == pytest.approx(100.0)


@pytest.mark.parametrize("nombre", ARCHIVOS_DEMO)
def test_rubrica_demo_puntajes_entre_0_y_5(nombre: str) -> None:
    """Todos los puntajes de nivel están en la escala 0–5."""
    rubrica = _cargar(nombre)
    fuera_de_rango = [
        (criterio.id, nivel.nombre, nivel.puntaje)
        for criterio in rubrica.criterios
        for nivel in criterio.niveles
        if not 0.0 <= nivel.puntaje <= 5.0
    ]
    assert fuera_de_rango == []
