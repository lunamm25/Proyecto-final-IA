"""Tests de los puntajes asignados por código y del título completo en la extracción."""

import time
from pathlib import Path

from app.ia import rubricas as rubricas_ia
from app.ia.providers import FakeProvider
from app.ia.rubricas import (
    asignar_puntajes,
    extraer_rubrica,
    extraer_texto_documento,
    numeros_del_documento,
    quitar_encabezados_pagina,
)
from app.ia.schemas import RubricaSchema
from app.services.rubricas import validar_rubrica

FIXTURES = Path(__file__).parent / "fixtures"

TEXTO_RANGOS = (
    "Rúbrica de evaluación\n"
    "Criterio | Peso | Excelente (4.5-5.0) | Competente (3.5-4.4) | Insuficiente (0.0-3.4)\n"
    "1. Mapa mental | 100 % | Relacional. | Parcial. | Superficial."
)
TEXTO_PLANTILLA = (
    "Laboratorio 2\nCriterio | Puntos | Evidencia esperada\n"
    "Arquitectura conceptual | 60 | Flujo end-to-end coherente.\n"
    "Datos y trazabilidad | 40 | Fuentes identificadas."
)


def _niveles(*pares: tuple[str, float]) -> list[dict]:
    return [{"nombre": n, "puntaje": p, "descriptor": f"Descriptor {n}"} for n, p in pares]


def _rubrica(niveles: list[dict], titulo: str = "Rúbrica", ponderacion: float = 100) -> dict:
    return {
        "titulo": titulo,
        "criterios": [
            {
                "id": "c1",
                "competencia": "Competencia",
                "nombre": "Criterio",
                "ponderacion": ponderacion,
                "niveles": niveles,
            }
        ],
    }


def _puntajes(rubrica: RubricaSchema) -> list[float]:
    return [n.puntaje for n in rubrica.criterios[0].niveles]


# ---------- Puntajes literales conservados ----------


def test_rango_cuenta_su_punto_medio_como_literal() -> None:
    numeros = {str(n) for n in numeros_del_documento(TEXTO_RANGOS)}
    assert {"4.75", "3.95", "1.70"} <= numeros


def test_puntajes_de_rangos_se_conservan() -> None:
    respuesta = _rubrica(
        _niveles(("Excelente", 4.75), ("Competente", 3.95), ("Insuficiente", 1.7))
    )
    rubrica = extraer_rubrica(TEXTO_RANGOS, FakeProvider([respuesta]))
    assert _puntajes(rubrica) == [4.75, 3.95, 1.7]


def test_puntajes_enteros_literales_no_se_reemplazan() -> None:
    texto = "Rúbrica\nNiveles: Alto 5 puntos | Medio 3 puntos | Bajo 1 punto\nCódigo | 100"
    respuesta = _rubrica(_niveles(("Alto", 5), ("Medio", 3), ("Bajo", 1)))
    rubrica = extraer_rubrica(texto, FakeProvider([respuesta]))
    assert _puntajes(rubrica) == [5, 3, 1]


def test_coma_decimal_cuenta_como_literal() -> None:
    texto = "Excelente 4,8 | Aceptable 3,2 | Deficiente 1,5"
    rubrica = RubricaSchema.model_validate(
        _rubrica(_niveles(("Excelente", 4.8), ("Aceptable", 3.2), ("Deficiente", 1.5)))
    )
    assert _puntajes(asignar_puntajes(rubrica, texto)) == [4.8, 3.2, 1.5]


# ---------- Puntajes asignados por código (plantilla sin números) ----------


def test_plantilla_con_ceros_recibe_5_35_0() -> None:
    respuesta = _rubrica(_niveles(("Excelente", 0), ("Competente", 0), ("Insuficiente", 0)))
    rubrica = extraer_rubrica(TEXTO_PLANTILLA, FakeProvider([respuesta]))
    assert _puntajes(rubrica) == [5.0, 3.5, 0.0]
    assert validar_rubrica(rubrica.model_dump()) == []


def test_puntajes_inventados_por_el_modelo_se_reemplazan() -> None:
    respuesta = _rubrica(_niveles(("Excelente", 4.2), ("Competente", 2.7), ("Insuficiente", 0.9)))
    rubrica = extraer_rubrica(TEXTO_PLANTILLA, FakeProvider([respuesta]))
    assert _puntajes(rubrica) == [5.0, 3.5, 0.0]


def test_asignacion_respeta_el_orden_y_conserva_nombres_y_descriptores() -> None:
    respuesta = _rubrica(_niveles(("Logrado", 0), ("En proceso", 0), ("No logrado", 0)))
    rubrica = extraer_rubrica(TEXTO_PLANTILLA, FakeProvider([respuesta]))
    niveles = rubrica.criterios[0].niveles
    assert [n.nombre for n in niveles] == ["Logrado", "En proceso", "No logrado"]
    assert niveles[0].descriptor == "Descriptor Logrado"


# ---------- Cantidad de niveles distinta de 3: no se asigna ----------


def test_cuatro_niveles_sin_puntajes_quedan_como_los_devolvio_el_modelo() -> None:
    respuesta = _rubrica(
        _niveles(("Superior", 0), ("Alto", 0), ("Básico", 0), ("Bajo", 0))
    )
    rubrica = extraer_rubrica(TEXTO_PLANTILLA, FakeProvider([respuesta]))
    assert _puntajes(rubrica) == [0, 0, 0, 0]
    inconsistencias = validar_rubrica(rubrica.model_dump())
    assert any("puntaje repetido" in e for e in inconsistencias)


def test_dos_niveles_inventados_no_se_tocan() -> None:
    respuesta = _rubrica(_niveles(("Cumple", 4.2), ("No cumple", 1.3)))
    rubrica = extraer_rubrica(TEXTO_PLANTILLA, FakeProvider([respuesta]))
    assert _puntajes(rubrica) == [4.2, 1.3]


# ---------- Título completo con subtítulo ----------

TEXTO_CON_ENCABEZADOS = "\n".join(
    [
        "UNIVERSIDAD X | CURSO DE IA",
        "LAB 01 - CIUDAD RESILIENTE | Pagina 1",
        "LAB 01",
        "CIUDAD RESILIENTE",
        "Diseno de soluciones digitales para gestion post-",
        "terremoto",
        "Criterio | Puntos",
        "Arquitectura | 100",
        "UNIVERSIDAD X | CURSO DE IA",
        "LAB 01 - CIUDAD RESILIENTE | Pagina 2",
        "Texto de la pagina 2",
        "UNIVERSIDAD X | CURSO DE IA",
        "LAB 01 - CIUDAD RESILIENTE | Pagina 3",
        "Texto de la pagina 3",
    ]
)
TITULO_COMPLETO = (
    "LAB 01 - CIUDAD RESILIENTE - Diseno de soluciones digitales para gestion post-terremoto"
)


def test_se_quitan_encabezados_y_se_conserva_el_subtitulo() -> None:
    limpio = quitar_encabezados_pagina(TEXTO_CON_ENCABEZADOS)
    assert "UNIVERSIDAD X" not in limpio
    assert "Pagina" not in limpio.replace("pagina", "")
    assert "Diseno de soluciones digitales para gestion post-" in limpio
    assert limpio.startswith("LAB 01\nCIUDAD RESILIENTE")


def test_titulo_con_subtitulo_llega_completo() -> None:
    proveedor = FakeProvider([_rubrica(_niveles(("A", 5), ("B", 0)), titulo=TITULO_COMPLETO)])
    rubrica = extraer_rubrica(TEXTO_CON_ENCABEZADOS, proveedor)
    assert rubrica.titulo == TITULO_COMPLETO
    prompt = proveedor.prompts_recibidos[0]
    assert "incluyendo el subtítulo" in prompt
    assert "terremoto" in prompt
    assert "UNIVERSIDAD X | CURSO DE IA" not in prompt


def test_encabezados_reales_de_manizales() -> None:
    texto = extraer_texto_documento(FIXTURES / "rubrica_manizales.pdf")
    limpio = quitar_encabezados_pagina(texto)
    assert "UNIVERSIDAD DE MANIZALES | PROFUNDIZACION" not in limpio
    assert "| Pagina" not in limpio
    assert "Diseno de soluciones digitales inteligentes" in limpio
    assert "Arquitectura conceptual 15" in limpio
    assert "Actor Necesidad Caso de uso" in limpio


def test_texto_sin_marcas_de_pagina_no_cambia() -> None:
    texto = "Título\nSubtítulo\nCumple\nCumple\nCumple"
    assert quitar_encabezados_pagina(texto) == texto


# ---------- Hallazgos de la revisión de calidad y seguridad ----------


def test_numero_suelto_lejos_del_nivel_no_cuenta_como_puntaje() -> None:
    texto = extraer_texto_documento(FIXTURES / "rubrica_lab01.md")
    assert "10 min" in texto
    respuesta = _rubrica(_niveles(("Excelente", 10), ("Competente", 5), ("Insuficiente", 0)))
    rubrica = extraer_rubrica(texto, FakeProvider([respuesta]))
    assert _puntajes(rubrica) == [5.0, 3.5, 0.0]


def test_rango_en_la_linea_siguiente_al_nombre_cuenta() -> None:
    texto = "Excelente\n(4.5-5.0)\nCompetente\n(3.5-4.4)\nInsuficiente\n(0.0-3.4)"
    rubrica = RubricaSchema.model_validate(
        _rubrica(_niveles(("Excelente", 4.75), ("Competente", 3.95), ("Insuficiente", 1.7)))
    )
    assert _puntajes(asignar_puntajes(rubrica, texto)) == [4.75, 3.95, 1.7]


def test_cadena_enorme_de_digitos_se_procesa_rapido() -> None:
    inicio = time.perf_counter()
    numeros_del_documento("1" * 100_000 + "-" + "2" * 100_000)
    assert time.perf_counter() - inicio < 1.0


def test_rango_con_numeros_enormes_no_lanza_error() -> None:
    texto = "99999999999999999999999999.99-99999999999999999999999999.99"
    assert isinstance(numeros_del_documento(texto), set)


def test_puntajes_no_finitos_se_reemplazan_con_tres_niveles() -> None:
    rubrica = RubricaSchema.model_validate(
        _rubrica(_niveles(("A", float("nan")), ("B", float("inf")), ("C", 1)))
    )
    assert _puntajes(asignar_puntajes(rubrica, "A 1 | B 2 | C 1")) == [5.0, 3.5, 0.0]


def test_cargar_prompt_conserva_separador_dentro_del_cuerpo(tmp_path, monkeypatch) -> None:
    (tmp_path / "con_cuerpo.md").write_text(
        "version: 2.0\n\nIntro del prompt\n---\nResto del prompt\n", encoding="utf-8"
    )
    (tmp_path / "con_cabecera.md").write_text(
        "version: 2.0\ncambios:\n- 2.0: algo\n---\nCuerpo\n", encoding="utf-8"
    )
    monkeypatch.setattr(rubricas_ia, "CARPETA_PROMPTS", tmp_path)
    assert rubricas_ia.cargar_prompt("con_cuerpo")[1] == "Intro del prompt\n---\nResto del prompt\n"
    assert rubricas_ia.cargar_prompt("con_cabecera") == ("2.0", "Cuerpo\n")
