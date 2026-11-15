"""Tests de la verificación anti-alucinación de citas (RF-05 CA3)."""

import pytest

from app.ia import citas
from app.ia.citas import (
    LIMITE_CARACTERES_FRAGMENTO,
    LIMITE_CARACTERES_FUENTE,
    UMBRAL_SIMILITUD,
    normalizar_fuente,
    normalizar_texto,
    verificar_cita,
    verificar_citas,
)
from app.ia.schemas import Evidencia

INFORME = (
    "En este laboratorio ejecutamos el agente con Ollama en modo solo lectura.\n"
    "El agente inspeccionó los 12 archivos ficticios y propuso un plan de organización.\n"
    "Después verificamos la integridad con SHA-256 y todos los hashes coincidieron."
)


def _evidencia(fragmento: str) -> Evidencia:
    """Crea una evidencia del informe con el fragmento dado."""
    return Evidencia(fragmento=fragmento, fuente="informe")


def test_normalizar_quita_acentos_mayusculas_y_espacios() -> None:
    """La normalización deja minúsculas, sin tildes y con espacios simples."""
    assert normalizar_texto("  Inspeccionó   LOS\n\tArchivos  ") == "inspecciono los archivos"


def test_cita_exacta_queda_verificada() -> None:
    """Una cita copiada literalmente del informe se verifica con similitud 100."""
    resultado = verificar_cita(_evidencia("propuso un plan de organización"), INFORME, "c1")
    assert resultado.verificada
    assert resultado.similitud == 100.0
    assert resultado.criterio_id == "c1"


def test_cita_con_pequenos_errores_queda_verificada() -> None:
    """Diferencias de tildes, mayúsculas, espacios y una errata siguen siendo verificadas."""
    resultado = verificar_cita(
        _evidencia("El agente  INSPECCIONO los 12 archivos fictcios"), INFORME
    )
    assert resultado.verificada
    assert resultado.similitud >= UMBRAL_SIMILITUD


def test_cita_inventada_no_queda_verificada() -> None:
    """Una cita que no aparece en el material se marca como no verificada."""
    resultado = verificar_cita(
        _evidencia("implementamos una red neuronal convolucional con PyTorch"), INFORME
    )
    assert not resultado.verificada
    assert resultado.similitud < UMBRAL_SIMILITUD


def test_material_vacio_no_verifica() -> None:
    """Sin texto fuente ninguna cita puede verificarse."""
    assert not verificar_cita(_evidencia("cualquier cosa"), "").verificada


def test_verificar_varias_citas_mantiene_el_orden() -> None:
    """Se devuelve un resultado por evidencia y en el mismo orden."""
    resultados = verificar_citas(
        [_evidencia("todos los hashes coincidieron"), _evidencia("usamos Docker Swarm")],
        INFORME,
        "c2",
    )
    assert [r.verificada for r in resultados] == [True, False]
    assert all(r.criterio_id == "c2" for r in resultados)


@pytest.mark.parametrize(
    "cita", ["el", "agente", "el agente", "el agente con", "hashes coincidieron"]
)
def test_citas_demasiado_cortas_no_se_verifican(cita: str) -> None:
    """Exige 3 palabras y 15 caracteres: palabras sueltas presentes en la fuente no cuentan."""
    assert normalizar_texto(cita) in normalizar_texto(INFORME)
    assert not verificar_cita(_evidencia(cita), INFORME).verificada


def test_cita_que_cumple_ambos_minimos_se_verifica() -> None:
    """Una cita de 3 palabras y al menos 15 caracteres presente en la fuente se verifica."""
    assert verificar_cita(_evidencia("modo solo lectura"), INFORME).verificada


def test_cita_mas_larga_que_la_fuente_no_se_verifica() -> None:
    """Si la cita es más larga que el material, no puede estar contenida en él."""
    inventada = (
        "Ejecutamos todas las pruebas unitarias e integración y el sistema respondió "
        "perfectamente siempre"
    )
    assert "pruebas" in inventada and len(inventada) >= 85
    resultado = verificar_cita(_evidencia(inventada), "pruebas")
    assert not resultado.verificada
    assert resultado.similitud == 0.0


def test_fuente_se_normaliza_una_sola_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    """verificar_citas normaliza el texto fuente una vez aunque haya varias evidencias."""
    llamadas: list[int] = []
    original = citas.normalizar_fuente

    def contar(texto: str) -> str:
        """Cuenta las llamadas y delega en la función real."""
        llamadas.append(len(texto))
        return original(texto)

    monkeypatch.setattr(citas, "normalizar_fuente", contar)
    resultados = verificar_citas([_evidencia("todos los hashes coincidieron")] * 5, INFORME)
    assert len(resultados) == 5 and all(r.verificada for r in resultados)
    assert llamadas == [len(INFORME)]


def test_fuente_enorme_se_recorta_al_tope() -> None:
    """Una fuente gigante se recorta al tope; las citas más allá quedan no verificadas."""
    fuente = "palabra " * (LIMITE_CARACTERES_FUENTE // 4) + "esta frase final queda fuera"
    assert len(normalizar_fuente(fuente)) <= LIMITE_CARACTERES_FUENTE
    assert not verificar_cita(_evidencia("esta frase final queda fuera"), fuente).verificada
    assert verificar_cita(_evidencia("palabra palabra palabra"), fuente).verificada


def test_fragmento_enorme_no_se_verifica() -> None:
    """Un fragmento por encima del tope se marca no verificado aunque esté en la fuente."""
    fuente = "texto real del estudiante " * 200
    fragmento = fuente[: LIMITE_CARACTERES_FRAGMENTO + 100]
    resultado = verificar_cita(_evidencia(fragmento), fuente)
    assert not resultado.verificada
    assert resultado.similitud == 0.0
