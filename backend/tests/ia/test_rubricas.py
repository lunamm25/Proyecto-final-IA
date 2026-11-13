"""Tests de la extracción de rúbricas usando solo FakeProvider (sin gastar API)."""

import io
from pathlib import Path

import pytest

from app.ia.providers import FakeProvider
from app.ia.rubricas import (
    VERSION_PROMPT_EXTRAER_RUBRICA,
    cargar_prompt,
    extraer_rubrica,
    extraer_texto_documento,
)
from app.ia.schemas import RubricaSchema

FIXTURES = Path(__file__).parent / "fixtures"
TEXTO = "Rúbrica Lab 1\nCriterio | Puntos\nCódigo limpio | 60\nInforme | 40"


def _rubrica() -> dict:
    return {
        "titulo": "Rúbrica Lab 1",
        "criterios": [
            {
                "id": "c1",
                "competencia": "Código limpio",
                "nombre": "Código limpio",
                "ponderacion": 60,
                "niveles": [
                    {"nombre": "Excelente", "puntaje": 5, "descriptor": "Cumple"},
                    {"nombre": "Insuficiente", "puntaje": 1, "descriptor": "No cumple"},
                ],
            },
            {
                "id": "c2",
                "competencia": "Informe",
                "nombre": "Informe",
                "ponderacion": 40,
                "niveles": [],
            },
        ],
    }


def test_extraccion_valida_devuelve_rubrica() -> None:
    proveedor = FakeProvider([_rubrica()])
    rubrica = extraer_rubrica(TEXTO, proveedor)
    assert isinstance(rubrica, RubricaSchema)
    assert [c.id for c in rubrica.criterios] == ["c1", "c2"]
    assert rubrica.criterios[0].ponderacion == 60


def test_prompt_incluye_texto_y_reglas_clave() -> None:
    proveedor = FakeProvider([_rubrica()])
    extraer_rubrica(TEXTO, proveedor)
    prompt = proveedor.prompts_recibidos[0]
    assert TEXTO in prompt
    assert "{texto_rubrica}" not in prompt
    assert "punto medio" in prompt
    assert "límite superior" not in prompt
    assert "Excelente, Competente, Insuficiente" in prompt
    assert "5.0, 3.5 y 0.0" in prompt
    assert "evidencia esperada" in prompt
    assert "incluyendo el subtítulo" in prompt
    assert "nómbralos de forma concreta" in prompt
    assert "sin normalizarla" in prompt
    assert "NO calculas notas" in prompt
    assert not prompt.startswith("version:")


@pytest.mark.parametrize("texto", ["", "   \n\t"])
def test_texto_vacio_lanza_error(texto: str) -> None:
    proveedor = FakeProvider([_rubrica()])
    with pytest.raises(ValueError, match="vacío"):
        extraer_rubrica(texto, proveedor)
    assert proveedor.prompts_recibidos == []


def test_respuesta_invalida_reintenta() -> None:
    invalida = {"titulo": "Lab", "criterios": [{"id": "c1", "nombre": "Sin campos"}]}
    proveedor = FakeProvider([invalida, _rubrica()])
    rubrica = extraer_rubrica(TEXTO, proveedor)
    assert rubrica.titulo == "Rúbrica Lab 1"
    assert len(proveedor.prompts_recibidos) == 2
    assert "Error de validación" in proveedor.prompts_recibidos[1]


def test_cargar_prompt_devuelve_version() -> None:
    version, cuerpo = cargar_prompt("extraer_rubrica")
    assert version == "1.0"
    assert VERSION_PROMPT_EXTRAER_RUBRICA == "1.0"
    assert "{texto_rubrica}" in cuerpo


def test_cargar_prompt_inexistente_falla() -> None:
    with pytest.raises(FileNotFoundError):
        cargar_prompt("no_existe")


def test_texto_de_markdown() -> None:
    texto = extraer_texto_documento(FIXTURES / "rubrica_lab01.md")
    assert "Rúbrica de evaluación" in texto


def test_texto_de_docx_incluye_tablas() -> None:
    texto = extraer_texto_documento(FIXTURES / "rubrica_fundamentos_ia.docx")
    assert "Rúbrica de evaluación" in texto
    assert "Criterio | Peso | Excelente (4.5-5.0)" in texto
    assert "5. Reto integrador | 25 %" in texto


def test_texto_de_pdf_incluye_rubrica() -> None:
    texto = extraer_texto_documento(FIXTURES / "rubrica_manizales.pdf")
    assert "Banco de Prompts" in texto
    assert "12. Rubrica de evaluacion - 100 puntos" in texto
    assert "Formulacion del problema y valor 10" in texto


def test_pdf_sin_texto_extraible_falla() -> None:
    from pypdf import PdfWriter

    escritor = PdfWriter()
    escritor.add_blank_page(width=200, height=200)
    salida = io.BytesIO()
    escritor.write(salida)
    with pytest.raises(ValueError, match="no tiene texto extraíble"):
        extraer_texto_documento(salida.getvalue(), "vacio.pdf")


def test_pdf_danado_falla() -> None:
    with pytest.raises(ValueError, match="No se pudo leer"):
        extraer_texto_documento(b"no soy un pdf", "rubrica.pdf")


def test_texto_desde_bytes() -> None:
    datos = (FIXTURES / "rubrica_lab01.md").read_bytes()
    assert extraer_texto_documento(datos, "rubrica.md").startswith("# LABORATORIO 01")


def test_bytes_sin_nombre_falla() -> None:
    with pytest.raises(ValueError, match="nombre"):
        extraer_texto_documento(b"hola")


@pytest.mark.parametrize("nombre", ["rubrica.xlsx", "rubrica.doc"])
def test_formato_no_soportado(nombre: str) -> None:
    with pytest.raises(ValueError, match="no soportado"):
        extraer_texto_documento(b"datos", nombre)
