"""Los reintentos del flujo (evaluador, mapeo, informe) respetan max_retries del proveedor."""

from pathlib import Path

import pytest

from app.ia.comun import ErrorIA
from app.ia.evaluador import ErrorEvaluacion, evaluar_laboratorio
from app.ia.informe import ErrorInforme, generar_informe_narrativo
from app.ia.providers import FakeProvider, texto_intentos
from app.ia.schemas import RubricaSchema
from app.ia.tematicas import ErrorMapeo, mapear_criterios_a_tematicas

RUBRICA = RubricaSchema.model_validate_json(
    (Path(__file__).parent / "fixtures" / "rubricas_demo" / "rubrica_lab03.json").read_text(
        encoding="utf-8"
    )
)
DATOS = {"laboratorios": [{"laboratorio": "LAB03", "cohorte": "Cohorte 1", "nota": 3.9}]}


def _evaluar(proveedor: FakeProvider) -> None:
    evaluar_laboratorio(RUBRICA, "Lab", "Objetivo", "Informe.", None, {}, proveedor)


def _mapear(proveedor: FakeProvider) -> None:
    mapear_criterios_a_tematicas(RUBRICA, ["Agentes de IA"], proveedor)


def _informe(proveedor: FakeProvider) -> None:
    generar_informe_narrativo(DATOS, proveedor)


FLUJOS = [
    pytest.param(_evaluar, ErrorEvaluacion, id="evaluador"),
    pytest.param(_mapear, ErrorMapeo, id="mapeo"),
    pytest.param(_informe, ErrorInforme, id="informe"),
]
CASOS = [
    pytest.param({"max_retries": 0}, 1, id="cero"),
    pytest.param({"max_retries": 1}, 2, id="uno"),
    pytest.param({}, 3, id="por_defecto"),
]


@pytest.mark.parametrize(("flujo", "error_cls"), FLUJOS)
@pytest.mark.parametrize(("kwargs", "intentos"), CASOS)
def test_json_invalido_agota_los_intentos_de_max_retries(
    flujo, error_cls: type[ErrorIA], kwargs: dict, intentos: int
) -> None:
    """Con JSON inválido se hacen exactamente max_retries + 1 llamadas antes del error."""
    proveedor = FakeProvider(["no es json"] * 4, **kwargs)
    with pytest.raises(error_cls, match=rf"tras {texto_intentos(intentos)}\.") as info:
        flujo(proveedor)
    assert len(proveedor.prompts_recibidos) == intentos
    assert len(info.value.errores) == intentos
    assert len(proveedor.respuestas) == 4 - intentos


def test_texto_intentos_usa_singular_y_plural() -> None:
    assert texto_intentos(1) == "1 intento"
    assert texto_intentos(3) == "3 intentos"


def test_fake_provider_valida_max_retries() -> None:
    assert FakeProvider([], max_retries=5).max_retries == 2
    with pytest.raises(Exception, match="negativo"):
        FakeProvider([], max_retries=-1)
