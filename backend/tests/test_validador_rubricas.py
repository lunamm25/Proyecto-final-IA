"""Pruebas del validador de inconsistencias de rúbricas (RF-03 CA2)."""

import copy

import pytest

from app.services.rubricas import validar_rubrica


def rubrica_valida() -> dict:
    """Rúbrica correcta de dos criterios (60 % + 40 %)."""
    return {
        "titulo": "Laboratorio 1",
        "criterios": [
            {
                "id": "c1",
                "competencia": "Programación",
                "nombre": "Calidad del código",
                "ponderacion": 60,
                "niveles": [
                    {"nombre": "Excelente", "puntaje": 5, "descriptor": "Muy bien"},
                    {"nombre": "Bueno", "puntaje": 3, "descriptor": "Bien"},
                    {"nombre": "Insuficiente", "puntaje": 1, "descriptor": "Mal"},
                ],
            },
            {
                "id": "c2",
                "competencia": "Colaboración",
                "nombre": "Uso de Git",
                "ponderacion": 40,
                "niveles": [
                    {"nombre": "Alto", "puntaje": 5, "descriptor": "Commits claros"},
                    {"nombre": "Bajo", "puntaje": 0, "descriptor": "Sin commits"},
                ],
            },
        ],
    }


def con_descriptores(niveles):
    """Completa con un descriptor de relleno los niveles (dict) que no traen la clave."""
    if not isinstance(niveles, list):
        return niveles
    return [
        {**n, "descriptor": f"Descriptor {i}"}
        if isinstance(n, dict) and "descriptor" not in n
        else n
        for i, n in enumerate(niveles, start=1)
    ]


def con_cambio(indice: int, completar: bool = True, **campos) -> dict:
    """Copia de la rúbrica válida con campos cambiados en el criterio `indice`.

    Con `completar=True` los niveles nuevos sin clave `descriptor` reciben uno de
    relleno, para que cada test pruebe solo su regla.
    """
    r = copy.deepcopy(rubrica_valida())
    if completar and "niveles" in campos:
        campos["niveles"] = con_descriptores(campos["niveles"])
    r["criterios"][indice].update(campos)
    return r


def contiene(errores: list[str], *fragmentos: str) -> bool:
    """True si algún mensaje contiene todos los fragmentos."""
    return any(all(f in e for f in fragmentos) for e in errores)


# ---------- Rúbrica válida ----------


def test_rubrica_valida_sin_inconsistencias():
    assert validar_rubrica(rubrica_valida()) == []


def test_ponderaciones_decimales_dentro_de_tolerancia():
    r = rubrica_valida()
    r["criterios"][0]["ponderacion"] = 33.333
    r["criterios"][1]["ponderacion"] = 66.667
    assert validar_rubrica(r) == []


def test_puntajes_en_los_extremos_0_y_5_son_validos():
    r = con_cambio(0, niveles=[{"nombre": "A", "puntaje": 0.0}, {"nombre": "B", "puntaje": 5.0}])
    assert validar_rubrica(r) == []


# ---------- Regla 1: criterio sin niveles ----------


@pytest.mark.parametrize("niveles", [[], None])
def test_criterio_sin_niveles(niveles):
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == ['Criterio "c2" (Uso de Git): no tiene niveles de desempeño.']


def test_criterio_con_niveles_ausentes():
    r = rubrica_valida()
    del r["criterios"][1]["niveles"]
    assert validar_rubrica(r) == ['Criterio "c2" (Uso de Git): no tiene niveles de desempeño.']


# ---------- Regla 2: puntajes repetidos ----------


def test_niveles_con_puntaje_repetido():
    niveles = [
        {"nombre": "Alto", "puntaje": 5},
        {"nombre": "Medio", "puntaje": 3},
        {"nombre": "Otro medio", "puntaje": 3.0},
    ]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert len(errores) == 1
    assert contiene(errores, '"c2"', "repetido", "3", "Medio", "Otro medio")


# ---------- Regla 3: suma de ponderaciones ----------


def test_ponderaciones_no_suman_100():
    errores = validar_rubrica(con_cambio(1, ponderacion=30))
    assert errores == ["Las ponderaciones suman 90 % y deben sumar 100 %."]


def test_ponderaciones_fuera_de_tolerancia():
    errores = validar_rubrica(con_cambio(1, ponderacion=40.02))
    assert contiene(errores, "suman 100,02 %")


# ---------- Regla 4: ponderación negativa o cero ----------


def test_ponderacion_cero():
    r = con_cambio(0, ponderacion=100)
    r["criterios"][1]["ponderacion"] = 0
    errores = validar_rubrica(r)
    assert errores == ['Criterio "c2" (Uso de Git): la ponderación debe ser mayor que 0 (tiene 0).']


def test_ponderacion_negativa_y_suma():
    errores = validar_rubrica(con_cambio(1, ponderacion=-10))
    assert contiene(errores, '"c2"', "mayor que 0", "-10")
    assert contiene(errores, "suman 50 %")
    assert len(errores) == 2


# ---------- Regla 5: puntaje fuera de 0..5 ----------


@pytest.mark.parametrize("puntaje", [6, -1, 5.01])
def test_puntaje_fuera_de_rango(puntaje):
    niveles = [{"nombre": "Alto", "puntaje": puntaje}, {"nombre": "Bajo", "puntaje": 0}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert len(errores) == 1
    assert contiene(errores, '"c2"', '"Alto"', "fuera del rango 0 a 5")


# ---------- Regla 6: ids duplicados ----------


def test_ids_de_criterio_duplicados():
    errores = validar_rubrica(con_cambio(1, id="c1"))
    assert len(errores) == 1
    assert contiene(errores, 'id duplicado "c1"')


def test_id_duplicado_se_reporta_una_sola_vez():
    r = rubrica_valida()
    tercero = copy.deepcopy(r["criterios"][1])
    r["criterios"][0]["ponderacion"] = 20
    r["criterios"].append(tercero)
    errores = validar_rubrica(r)
    assert sum('id duplicado "c2"' in e for e in errores) == 1


# ---------- Regla 7: sin criterios ----------


@pytest.mark.parametrize("criterios", [[], None])
def test_rubrica_sin_criterios(criterios):
    assert validar_rubrica({"titulo": "X", "criterios": criterios}) == [
        "La rúbrica no tiene criterios."
    ]


def test_rubrica_sin_campo_criterios():
    assert validar_rubrica({"titulo": "X"}) == ["La rúbrica no tiene criterios."]


# ---------- Varias inconsistencias a la vez ----------


def test_reporta_todas_las_inconsistencias():
    r = rubrica_valida()
    r["criterios"][0]["niveles"] = con_descriptores(
        [
            {"nombre": "A", "puntaje": 7},
            {"nombre": "B", "puntaje": 2},
            {"nombre": "C", "puntaje": 2},
        ]
    )
    r["criterios"][1]["niveles"] = []
    r["criterios"][1]["ponderacion"] = 10
    errores = validar_rubrica(r)
    assert contiene(errores, '"c1"', '"A"', "fuera del rango")
    assert contiene(errores, '"c1"', "repetido", "2")
    assert contiene(errores, '"c2"', "no tiene niveles")
    assert contiene(errores, "suman 70 %")
    assert len(errores) == 4
    assert len(errores) == len(set(errores))


def test_mensajes_incluyen_id_y_nombre_del_criterio():
    errores = validar_rubrica(con_cambio(0, ponderacion=0))
    assert any(e.startswith('Criterio "c1" (Calidad del código):') for e in errores)


# ---------- Robustez: nunca lanza excepción ----------


@pytest.mark.parametrize("basura", [None, [], [1, 2], "texto", 42, True, 3.5])
def test_rubrica_que_no_es_diccionario(basura):
    errores = validar_rubrica(basura)
    assert errores == ["La rúbrica debe ser un objeto JSON con 'titulo' y 'criterios'."]


@pytest.mark.parametrize("criterios", ["c1", {"id": "c1"}, 5])
def test_criterios_que_no_es_lista(criterios):
    assert validar_rubrica({"criterios": criterios}) == [
        "El campo 'criterios' debe ser una lista."
    ]


def test_criterio_que_no_es_diccionario():
    r = rubrica_valida()
    r["criterios"].append("no soy un criterio")
    errores = validar_rubrica(r)
    assert errores == ["Criterio en la posición 3: debe ser un objeto JSON."]


@pytest.mark.parametrize("valor", [None, "", "   ", 7])
def test_criterio_sin_id(valor):
    r = con_cambio(1, id=valor)
    errores = validar_rubrica(r)
    assert errores == ["Criterio en la posición 2 (Uso de Git): no tiene id."]


def test_criterio_sin_id_ni_nombre():
    r = rubrica_valida()
    del r["criterios"][1]["id"]
    del r["criterios"][1]["nombre"]
    assert validar_rubrica(r) == [
        "Criterio en la posición 2: no tiene id.",
        "Criterio en la posición 2: no tiene nombre.",
    ]


def test_ponderacion_ausente():
    r = rubrica_valida()
    del r["criterios"][1]["ponderacion"]
    errores = validar_rubrica(r)
    assert contiene(errores, '"c2"', "no tiene ponderación")
    assert contiene(errores, "suman 60 %", "1 criterio")


@pytest.mark.parametrize("valor", ["40", True, False, [40], {"v": 40}, float("nan")])
def test_ponderacion_no_numerica(valor):
    errores = validar_rubrica(con_cambio(1, ponderacion=valor))
    assert contiene(errores, '"c2"', "ponderación debe ser un número")


@pytest.mark.parametrize("valor", ["5", True, None, [5], float("inf")])
def test_puntaje_no_numerico_o_ausente(valor):
    niveles = [{"nombre": "Alto", "puntaje": valor}, {"nombre": "Bajo", "puntaje": 0}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert len(errores) == 1
    assert contiene(errores, '"c2"', '"Alto"', "puntaje")


def test_nivel_sin_campo_puntaje():
    niveles = [{"nombre": "Alto"}, {"nombre": "Bajo", "puntaje": 0}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == ['Criterio "c2" (Uso de Git): el nivel "Alto" no tiene puntaje.']


@pytest.mark.parametrize("niveles", ["Alto, Bajo", {"nombre": "Alto"}, 3])
def test_niveles_que_no_es_lista(niveles):
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == ["Criterio \"c2\" (Uso de Git): el campo 'niveles' debe ser una lista."]


def test_nivel_que_no_es_diccionario():
    niveles = [{"nombre": "Alto", "puntaje": 5}, "Bajo"]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == [
        'Criterio "c2" (Uso de Git): el nivel en la posición 2 debe ser un objeto JSON.'
    ]


def test_nivel_sin_nombre_se_identifica_por_posicion():
    niveles = [{"puntaje": 9}, {"nombre": "Bajo", "puntaje": 0}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert contiene(errores, "nivel en la posición 1", "fuera del rango")


def test_no_modifica_la_rubrica_recibida():
    r = con_cambio(1, niveles=[], ponderacion="x")
    original = copy.deepcopy(r)
    validar_rubrica(r)
    assert r == original


def test_todos_los_criterios_basura_no_reporta_suma():
    assert validar_rubrica({"criterios": [1, None]}) == [
        "Criterio en la posición 1: debe ser un objeto JSON.",
        "Criterio en la posición 2: debe ser un objeto JSON.",
    ]


# ---------- Reglas añadidas (decisión del equipo, 13 nov 2026) ----------


def test_criterio_con_un_solo_nivel():
    niveles = [{"nombre": "Alto", "puntaje": 5}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == [
        'Criterio "c2" (Uso de Git): debe tener al menos 2 niveles de desempeño (tiene 1).'
    ]


def test_criterio_con_un_solo_nivel_invalido_reporta_ambas_cosas():
    niveles = [{"nombre": "Alto", "puntaje": 9}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert contiene(errores, '"c2"', "al menos 2 niveles")
    assert contiene(errores, '"c2"', '"Alto"', "fuera del rango")


def test_dos_niveles_es_el_minimo_valido():
    niveles = [{"nombre": "Alto", "puntaje": 5}, {"nombre": "Bajo", "puntaje": 0}]
    assert validar_rubrica(con_cambio(1, niveles=niveles)) == []


def test_nombres_de_nivel_repetidos():
    niveles = [{"nombre": "Bueno", "puntaje": 5}, {"nombre": "Bueno", "puntaje": 3}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == ['Criterio "c2" (Uso de Git): hay 2 niveles con el nombre repetido "Bueno".']


def test_nombres_repetidos_con_espacios_cuentan_como_iguales():
    niveles = [{"nombre": "Bueno", "puntaje": 5}, {"nombre": " Bueno ", "puntaje": 3}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert contiene(errores, '"c2"', 'nombre repetido "Bueno"')


def test_nombre_y_puntaje_repetidos_se_reportan_por_separado():
    niveles = [{"nombre": "Bueno", "puntaje": 3}, {"nombre": "Bueno", "puntaje": 3}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert contiene(errores, "nombre repetido")
    assert contiene(errores, "puntaje repetido 3")
    assert len(errores) == 2


def test_niveles_sin_nombre_no_cuentan_como_repetidos():
    niveles = [{"puntaje": 5}, {"puntaje": 0}]
    assert not contiene(validar_rubrica(con_cambio(1, niveles=niveles)), "nombre repetido")


def test_mensaje_puntaje_no_numerico_bien_redactado():
    niveles = [{"nombre": "Alto", "puntaje": "5"}, {"nombre": "Bajo", "puntaje": 0}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == [
        'Criterio "c2" (Uso de Git): el puntaje del nivel "Alto" debe ser un número.'
    ]
    assert not contiene(errores, "de el nivel")


def test_mensaje_puntaje_no_numerico_nivel_sin_nombre():
    niveles = [{"puntaje": "x"}, {"nombre": "Bajo", "puntaje": 0}]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert contiene(errores, "el puntaje del nivel en la posición 1 debe ser un número.")


# ---------- Competencia, nombre y descriptor obligatorios (14 nov 2026) ----------


@pytest.mark.parametrize("valor", [None, "", "   ", 5])
def test_criterio_sin_competencia(valor):
    errores = validar_rubrica(con_cambio(1, competencia=valor))
    assert errores == ['Criterio "c2" (Uso de Git): no tiene competencia.']


def test_criterio_sin_campo_competencia():
    r = rubrica_valida()
    del r["criterios"][1]["competencia"]
    assert validar_rubrica(r) == ['Criterio "c2" (Uso de Git): no tiene competencia.']


@pytest.mark.parametrize("valor", [None, "", "   ", 7])
def test_criterio_sin_nombre(valor):
    errores = validar_rubrica(con_cambio(1, nombre=valor))
    assert errores == ['Criterio "c2": no tiene nombre.']


def test_criterio_sin_campo_nombre():
    r = rubrica_valida()
    del r["criterios"][0]["nombre"]
    assert validar_rubrica(r) == ['Criterio "c1": no tiene nombre.']


@pytest.mark.parametrize("valor", [None, "", "  ", 3])
def test_nivel_sin_descriptor(valor):
    niveles = [
        {"nombre": "Alto", "puntaje": 5, "descriptor": valor},
        {"nombre": "Bajo", "puntaje": 0, "descriptor": "Sin commits"},
    ]
    errores = validar_rubrica(con_cambio(1, niveles=niveles))
    assert errores == ['Criterio "c2" (Uso de Git): el nivel "Alto" no tiene descriptor.']


def test_nivel_sin_campo_descriptor_ni_nombre():
    niveles = [{"puntaje": 5}, {"nombre": "Bajo", "puntaje": 0, "descriptor": "x"}]
    errores = validar_rubrica(con_cambio(1, completar=False, niveles=niveles))
    assert 'Criterio "c2" (Uso de Git): el nivel en la posición 1 no tiene descriptor.' in errores


def test_varios_campos_vacios_se_reportan_todos():
    r = con_cambio(0, competencia="", nombre=None)
    r["criterios"][1]["niveles"][0]["descriptor"] = ""
    errores = validar_rubrica(r)
    assert 'Criterio "c1": no tiene competencia.' in errores
    assert 'Criterio "c1": no tiene nombre.' in errores
    assert 'Criterio "c2" (Uso de Git): el nivel "Alto" no tiene descriptor.' in errores
    assert len(errores) == 3
