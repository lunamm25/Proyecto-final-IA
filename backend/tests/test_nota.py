"""Pruebas del cálculo determinista de la nota (REQUISITOS §8)."""

from decimal import Decimal
from itertools import product

import pytest

from app.services.nota import (
    NivelInvalidoError,
    ResultadoNota,
    RubricaInvalidaError,
    calcular_nota,
)

NIVELES_5_1 = [
    {"nombre": "Excelente", "puntaje": 5, "descriptor": "..."},
    {"nombre": "Bueno", "puntaje": 4, "descriptor": "..."},
    {"nombre": "Aceptable", "puntaje": 3, "descriptor": "..."},
    {"nombre": "Insuficiente", "puntaje": 1, "descriptor": "..."},
]


def _criterio(cid: str, ponderacion: float, niveles: list[dict] | None = None) -> dict:
    """Crea un criterio con la forma de RubricaSchema (como en rubrica_versiones.contenido)."""
    return {
        "id": cid,
        "competencia": "Competencia de prueba",
        "nombre": f"Criterio {cid}",
        "ponderacion": ponderacion,
        "niveles": niveles if niveles is not None else NIVELES_5_1,
    }


def _dos_criterios(peso_max: float) -> tuple[list[dict], dict[str, str]]:
    """Rúbrica de 2 criterios: el primero en máximo con peso_max %, el resto en mínimo."""
    criterios = [_criterio("c1", peso_max), _criterio("c2", 100 - peso_max)]
    return criterios, {"c1": "Excelente", "c2": "Insuficiente"}


RUBRICA_4 = [
    _criterio("c1", 25),
    _criterio("c2", 25),
    _criterio("c3", 25),
    _criterio("c4", 25),
]


# ---------- Tests obligatorios de §8 ----------


def test_suma_100_es_valida_y_devuelve_resultado():
    elegidos = {c["id"]: "Bueno" for c in RUBRICA_4}
    resultado = calcular_nota(RUBRICA_4, elegidos)
    assert isinstance(resultado, ResultadoNota)
    assert isinstance(resultado.nota, Decimal)


def test_todo_maximo_da_cinco():
    elegidos = {c["id"]: "Excelente" for c in RUBRICA_4}
    assert calcular_nota(RUBRICA_4, elegidos).nota == Decimal("5.0")


def test_todo_minimo_da_cero():
    elegidos = {c["id"]: "Insuficiente" for c in RUBRICA_4}
    assert calcular_nota(RUBRICA_4, elegidos).nota == Decimal("0.0")


def test_caso_mixto_conocido():
    # Cuenta a mano:
    #   c1 (30 %): niveles 5,4,3,1 -> elige "Bueno" (4): (4-1)/(5-1) = 0.75
    #              aporta 0.30 x 0.75 x 5 = 1.125
    #   c2 (40 %): niveles 10,6,2 -> elige "Medio" (6): (6-2)/(10-2) = 0.5
    #              aporta 0.40 x 0.5 x 5 = 1.0
    #   c3 (20 %): elige el máximo -> normalizado 1 -> aporta 0.20 x 1 x 5 = 1.0
    #   c4 (10 %): elige el mínimo -> normalizado 0 -> aporta 0
    #   Total = 1.125 + 1.0 + 1.0 + 0 = 3.125 -> redondeo a 1 decimal = 3.1
    niveles_10 = [
        {"nombre": "Alto", "puntaje": 10, "descriptor": "..."},
        {"nombre": "Medio", "puntaje": 6, "descriptor": "..."},
        {"nombre": "Bajo", "puntaje": 2, "descriptor": "..."},
    ]
    criterios = [
        _criterio("c1", 30),
        _criterio("c2", 40, niveles_10),
        _criterio("c3", 20),
        _criterio("c4", 10),
    ]
    elegidos = {"c1": "Bueno", "c2": "Medio", "c3": "Excelente", "c4": "Insuficiente"}
    assert calcular_nota(criterios, elegidos).nota == Decimal("3.1")


# ---------- Redondeo ROUND_HALF_UP ----------


@pytest.mark.parametrize(
    ("peso_max", "esperado"),
    [
        (45, "2.3"),  # 0.45 x 5 = 2.25 -> 2.3 (round() de Python daría 2.2)
        (3, "0.2"),  # 0.03 x 5 = 0.15 -> 0.2 (round(0.15, 1) en float da 0.1)
        (69, "3.5"),  # 0.69 x 5 = 3.45 -> 3.5
        (17, "0.9"),  # 0.17 x 5 = 0.85 -> 0.9 (round(0.85, 1) en float da 0.8)
        (44.8, "2.2"),  # 2.24 -> 2.2 (no sube si no llega a .x5)
        (45.2, "2.3"),  # 2.26 -> 2.3
    ],
)
def test_redondeo_half_up(peso_max, esperado):
    criterios, elegidos = _dos_criterios(peso_max)
    assert calcular_nota(criterios, elegidos).nota == Decimal(esperado)


def test_redondeo_python_seria_distinto():
    # Documenta por qué se usa ROUND_HALF_UP y no round(): el redondeo de Python difiere.
    assert round(2.25, 1) == 2.2
    assert round(0.15, 1) == 0.1


def test_redondeo_exacto_con_tercios():
    # c1 (3 %): niveles 0,1,3 -> elige 1: normalizado 1/3 -> aporta 0.03 x 1/3 x 5 = 0.05
    # Con aritmética inexacta saldría 0.0499... -> 0.0; con aritmética exacta 0.05 -> 0.1
    niveles_tercio = [
        {"nombre": "Nulo", "puntaje": 0, "descriptor": "..."},
        {"nombre": "Parcial", "puntaje": 1, "descriptor": "..."},
        {"nombre": "Total", "puntaje": 3, "descriptor": "..."},
    ]
    criterios = [_criterio("c1", 3, niveles_tercio), _criterio("c2", 97)]
    elegidos = {"c1": "Parcial", "c2": "Insuficiente"}
    assert calcular_nota(criterios, elegidos).nota == Decimal("0.1")


def test_nota_tiene_un_decimal():
    elegidos = {c["id"]: "Excelente" for c in RUBRICA_4}
    nota = calcular_nota(RUBRICA_4, elegidos).nota
    assert nota.as_tuple().exponent == -1


# ---------- Casos adicionales ----------


def test_niveles_en_orden_arbitrario():
    desordenados = [
        {"nombre": "Aceptable", "puntaje": 3, "descriptor": "..."},
        {"nombre": "Insuficiente", "puntaje": 1, "descriptor": "..."},
        {"nombre": "Excelente", "puntaje": 5, "descriptor": "..."},
        {"nombre": "Bueno", "puntaje": 4, "descriptor": "..."},
    ]
    criterios = [_criterio("c1", 100, desordenados)]
    assert calcular_nota(criterios, {"c1": "Excelente"}).nota == Decimal("5.0")
    assert calcular_nota(criterios, {"c1": "Insuficiente"}).nota == Decimal("0.0")
    # (4-1)/(5-1) = 0.75 -> 0.75 x 5 = 3.75 -> 3.8
    assert calcular_nota(criterios, {"c1": "Bueno"}).nota == Decimal("3.8")


def test_puntajes_no_enteros():
    # niveles 4.5, 3.2, 0.5 -> elige 3.2: (3.2-0.5)/(4.5-0.5) = 2.7/4 = 0.675
    # 0.675 x 5 = 3.375 -> 3.4
    niveles = [
        {"nombre": "A", "puntaje": 4.5, "descriptor": "..."},
        {"nombre": "B", "puntaje": 3.2, "descriptor": "..."},
        {"nombre": "C", "puntaje": 0.5, "descriptor": "..."},
    ]
    resultado = calcular_nota([_criterio("c1", 100, niveles)], {"c1": "B"})
    assert resultado.nota == Decimal("3.4")
    assert resultado.normalizados["c1"] == pytest.approx(0.675)


def test_un_solo_criterio_de_100():
    criterios = [_criterio("unico", 100)]
    assert calcular_nota(criterios, {"unico": "Excelente"}).nota == Decimal("5.0")
    assert calcular_nota(criterios, {"unico": "Aceptable"}).nota == Decimal("2.5")


def test_normalizados_devueltos():
    criterios = [_criterio("c1", 50), _criterio("c2", 30), _criterio("c3", 20)]
    elegidos = {"c1": "Excelente", "c2": "Aceptable", "c3": "Insuficiente"}
    resultado = calcular_nota(criterios, elegidos)
    assert resultado.normalizados == {"c1": 1.0, "c2": 0.5, "c3": 0.0}
    assert all(isinstance(v, float) for v in resultado.normalizados.values())


def test_nota_siempre_acotada_entre_0_y_5():
    criterios = [_criterio("c1", 33.33), _criterio("c2", 33.33), _criterio("c3", 33.34)]
    nombres = [n["nombre"] for n in NIVELES_5_1]
    for combinacion in product(nombres, repeat=3):
        elegidos = dict(zip(["c1", "c2", "c3"], combinacion, strict=True))
        nota = calcular_nota(criterios, elegidos).nota
        assert Decimal("0.0") <= nota <= Decimal("5.0")


def test_acotada_con_suma_en_borde_de_tolerancia():
    # Suma 100.01 (dentro de la tolerancia): todo máximo no debe pasar de 5.0
    criterios = [_criterio("c1", 50.01), _criterio("c2", 50)]
    elegidos = {"c1": "Excelente", "c2": "Excelente"}
    assert calcular_nota(criterios, elegidos).nota == Decimal("5.0")


def test_ponderaciones_decimales_que_suman_100():
    criterios = [_criterio("c1", 33.3), _criterio("c2", 33.3), _criterio("c3", 33.4)]
    elegidos = {"c1": "Excelente", "c2": "Excelente", "c3": "Excelente"}
    assert calcular_nota(criterios, elegidos).nota == Decimal("5.0")


# ---------- Rúbrica inválida / niveles inválidos lanzan error ----------


@pytest.mark.parametrize("pesos", [(50, 40), (60, 60), (99.98, 0)])
def test_ponderaciones_que_no_suman_100(pesos):
    criterios = [_criterio("c1", pesos[0]), _criterio("c2", pesos[1])]
    with pytest.raises(RubricaInvalidaError, match="100"):
        calcular_nota(criterios, {"c1": "Bueno", "c2": "Bueno"})


def test_ponderacion_negativa():
    criterios = [_criterio("c1", 120), _criterio("c2", -20)]
    with pytest.raises(RubricaInvalidaError):
        calcular_nota(criterios, {"c1": "Bueno", "c2": "Bueno"})


def test_rubrica_sin_criterios():
    with pytest.raises(RubricaInvalidaError):
        calcular_nota([], {})


def test_criterio_con_un_solo_nivel():
    niveles = [{"nombre": "Único", "puntaje": 5, "descriptor": "..."}]
    with pytest.raises(RubricaInvalidaError, match="2 niveles"):
        calcular_nota([_criterio("c1", 100, niveles)], {"c1": "Único"})


def test_criterio_con_max_igual_a_min():
    niveles = [
        {"nombre": "A", "puntaje": 3, "descriptor": "..."},
        {"nombre": "B", "puntaje": 3, "descriptor": "..."},
    ]
    with pytest.raises(RubricaInvalidaError, match="distintos"):
        calcular_nota([_criterio("c1", 100, niveles)], {"c1": "A"})


def test_ids_de_criterio_duplicados():
    criterios = [_criterio("c1", 50), _criterio("c1", 50)]
    with pytest.raises(RubricaInvalidaError, match="repetido"):
        calcular_nota(criterios, {"c1": "Bueno"})


def test_nivel_elegido_inexistente():
    criterios = [_criterio("c1", 100)]
    with pytest.raises(NivelInvalidoError, match="Sobresaliente"):
        calcular_nota(criterios, {"c1": "Sobresaliente"})


def test_criterio_sin_nivel_elegido():
    criterios = [_criterio("c1", 50), _criterio("c2", 50)]
    with pytest.raises(NivelInvalidoError, match="c2"):
        calcular_nota(criterios, {"c1": "Bueno"})


def test_criterio_elegido_que_no_existe_en_rubrica():
    criterios = [_criterio("c1", 100)]
    with pytest.raises(NivelInvalidoError, match="c9"):
        calcular_nota(criterios, {"c1": "Bueno", "c9": "Bueno"})


def test_errores_son_value_error():
    # Permite capturarlos de forma genérica en servicios/rutas.
    assert issubclass(RubricaInvalidaError, ValueError)
    assert issubclass(NivelInvalidoError, ValueError)
