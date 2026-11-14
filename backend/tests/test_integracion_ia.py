"""Integración sin red entre nuestros adaptadores y el motor de IA real de Rol 1.

Estos tests SÍ importan `app.ia.*`: usan el `FakeProvider` de Rol 1 (respuestas fijas, sin red)
a través de `evaluador_ia`, `informe_ia` y el endpoint del informe, para comprobar que los
adaptadores encajan con las firmas reales de `evaluar_laboratorio`, `generar_informe_narrativo`
y `mapear_criterios_a_tematicas`. El resto de tests del backend no importa `app.ia`.
"""

import json
from pathlib import Path

import pytest

from app.api.deps import obtener_ia_informe
from app.ia.providers import FakeProvider, OpenAICompatProvider
from app.ia.schemas import RubricaSchema
from app.services import evaluador_ia, informe_ia
from app.services.evaluaciones import ConfigEvaluacion
from app.services.evaluador_ia import ResultadoIA, SolicitudEvaluacion
from app.services.informe_ia import IAInformeReal, MapeoIA
from tests.test_auth import ajustes
from tests.test_informe_mapa import ID_EST, RUBRICA, escenario, informe  # noqa: F401

CARPETA_DEMO = Path(__file__).resolve().parents[1] / "rubricas_demo"
CARPETA_PROMPTS = Path(__file__).resolve().parents[1] / "app" / "ia" / "prompts"
CONFIG = ConfigEvaluacion("gemini", "gemini-3.5-flash-lite", 0.1)

TEXTO_INFORME = (
    "Implementé un agente que lee archivos CSV y genera un resumen con pandas. "
    "El informe explica las decisiones de diseño y cita las fuentes consultadas."
)

EVALUACION = {
    "criterios": [
        {
            "criterio_id": "C1",
            "nivel_elegido": "bueno",
            "evidencias": [
                {
                    "fragmento": "Implementé un agente que lee archivos CSV",
                    "fuente": "informe",
                    "ubicacion": "p. 1",
                }
            ],
            "justificacion": "El código cumple lo pedido.",
            "fortalezas": ["Uso de pandas"],
            "debilidades": ["Faltan pruebas"],
            "recomendacion": "Agregar pruebas unitarias.",
        },
        {
            "criterio_id": "C2",
            "nivel_elegido": "Bajo",
            "evidencias": [],
            "justificacion": "No hay evidencia suficiente.",
            "fortalezas": [],
            "debilidades": ["Informe breve"],
            "recomendacion": "Ampliar el informe.",
        },
    ],
    "aprendizajes_identificados": ["Lectura de archivos"],
    "como_aplico_conocimientos": "Aplicó pandas al problema.",
    "aspectos_a_fortalecer": ["Pruebas"],
    "retroalimentacion_general": "Buen trabajo.",
}

MAPEO = {
    "mapeos": [
        {"criterio_id": "C1", "tematicas": ["Redes neuronales"], "conceptos": ["Perceptrón"]},
        {"criterio_id": "C2", "tematicas": ["ética y verificación"], "conceptos": ["Citas"]},
    ]
}

NARRATIVA = {
    "competencias_desarrolladas": ["Programación sólida en los laboratorios."],
    "brechas": ["La comunicación escrita puede mejorar."],
    "plan_fortalecimiento": [
        {
            "accion": "Redactar un resumen por laboratorio",
            "recurso": "Guía de escritura técnica",
            "prioridad": "media",
            "competencia": "comunicación",
        }
    ],
    "conclusion": "Buen avance general en el curso.",
}


class FabricaFalsa:
    """Sustituye `construir_proveedor`: registra los argumentos y entrega un FakeProvider."""

    def __init__(self, respuestas: list[dict]) -> None:
        self.proveedor = FakeProvider(respuestas)
        self.llamadas: list[dict] = []

    def __call__(self, config, settings, **kwargs):
        self.llamadas.append(kwargs)
        return self.proveedor


def _solicitud() -> SolicitudEvaluacion:
    """Solicitud de evaluación con la rúbrica pequeña de los tests de informe."""
    return SolicitudEvaluacion(
        rubrica=RUBRICA,
        descripcion="Laboratorio de prueba",
        objetivos="Leer archivos con Python",
        texto_informe=TEXTO_INFORME,
        resumen_codigo=None,
        resultados_verificacion={"estatico": {"lint_errores": 0}},
        proveedor="gemini",
        modelo="gemini-3.5-flash-lite",
        temperatura=0.1,
    )


def test_evaluacion_real_con_fake_provider_se_traduce(monkeypatch):
    fabrica = FabricaFalsa([EVALUACION])
    monkeypatch.setattr(evaluador_ia, "construir_proveedor", fabrica)
    resultado = evaluador_ia.evaluar_con_ia(_solicitud())
    assert isinstance(resultado, ResultadoIA)
    assert [c.criterio_id for c in resultado.criterios] == ["C1", "C2"]
    assert resultado.criterios[0].nivel_elegido == "Bueno"  # nombre exacto de la rúbrica
    assert resultado.criterios[0].citas[0]["verificada"] is True
    assert resultado.criterios[1].evidencias == [] and resultado.criterios[1].citas == []
    assert resultado.retroalimentacion_general == "Buen trabajo."
    primera = (CARPETA_PROMPTS / "evaluar_laboratorio.md").read_text(encoding="utf-8")
    assert f"version: {resultado.version_prompt}" == primera.splitlines()[0]
    assert len(resultado.respuestas_crudas) == 1
    assert fabrica.llamadas == [{}]  # la evaluación no pasa timeout ni max_retries


def test_evaluacion_invalida_se_traduce_a_evaluacion_ia_error(monkeypatch):
    malo = {**EVALUACION, "criterios": EVALUACION["criterios"][:1]}
    fabrica = FabricaFalsa([malo, malo, malo])
    monkeypatch.setattr(evaluador_ia, "construir_proveedor", fabrica)
    with pytest.raises(evaluador_ia.EvaluacionIAError) as error:
        evaluador_ia.evaluar_con_ia(_solicitud())
    assert len(error.value.respuestas_crudas) == 3 and error.value.errores


def test_mapeo_real_con_fake_provider_se_traduce(monkeypatch):
    fabrica = FabricaFalsa([MAPEO])
    monkeypatch.setattr(informe_ia, "construir_proveedor", fabrica)
    tematicas = ["Aprendizaje automático", "Ética y verificación", "Redes neuronales"]
    mapeo = IAInformeReal().mapear(RUBRICA, tematicas, CONFIG)
    assert isinstance(mapeo, MapeoIA)
    assert [(m.criterio_id, m.tematicas, m.conceptos) for m in mapeo.criterios] == [
        ("C1", ["Redes neuronales"], ["Perceptrón"]),
        ("C2", ["Ética y verificación"], ["Citas"]),
    ]
    assert mapeo.proveedor == "fake" and mapeo.version_prompt
    assert fabrica.llamadas == [{}]


def test_informe_con_narrativa_y_mapeo_reales(cliente_api, escenario, monkeypatch):  # noqa: F811
    # 4 laboratorios publicados (4 versiones de rúbrica) → 4 mapeos y luego 1 narrativa.
    fabrica = FabricaFalsa([MAPEO, MAPEO, MAPEO, MAPEO, NARRATIVA])
    monkeypatch.setattr(informe_ia, "construir_proveedor", fabrica)
    cliente_api.app.dependency_overrides[obtener_ia_informe] = lambda: IAInformeReal()
    cuerpo = informe(cliente_api, ID_EST).json()
    narrativa = cuerpo["narrativa"]
    assert narrativa["estado"] == "generada", narrativa
    assert narrativa["competencias_desarrolladas"] == NARRATIVA["competencias_desarrolladas"]
    assert narrativa["plan_fortalecimiento"][0]["competencia"] == "Comunicación"
    assert cuerpo["promedio_general"] == 4.2  # los números siguen saliendo del backend
    assert {t["tematica"] for t in cuerpo["tematicas"]} >= {"Ética y verificación"}
    assert cuerpo["avisos"] == []  # todas las versiones quedaron mapeadas
    assert fabrica.llamadas == [{}] * 5  # ni el informe ni el mapeo pasan max_retries
    assert fabrica.proveedor.respuestas == []


def test_construir_proveedor_openai_compat_pasa_max_retries():
    config = ConfigEvaluacion("openai_compat", "modelo-x", 0.1)
    datos = ajustes(openai_compat_base_url="http://127.0.0.1:9/v1", openai_compat_api_key="k")
    proveedor = evaluador_ia.construir_proveedor(config, datos, timeout=3.0, max_retries=0)
    assert isinstance(proveedor, OpenAICompatProvider)
    assert proveedor.max_retries == 0
    por_defecto = evaluador_ia.construir_proveedor(config, datos)
    assert por_defecto.max_retries == 2


@pytest.mark.parametrize("archivo", sorted(p.name for p in CARPETA_DEMO.glob("*.json")))
def test_rubricas_demo_validan_con_rubrica_schema(archivo):
    contenido = json.loads((CARPETA_DEMO / archivo).read_text(encoding="utf-8"))
    rubrica = RubricaSchema.model_validate(contenido)
    assert rubrica.criterios
