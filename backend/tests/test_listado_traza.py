"""Pruebas de GET /api/evaluaciones (listado docente) y GET /api/evaluaciones/{id}/traza."""

import copy
from datetime import datetime
from decimal import Decimal

import pytest

from app.models import Auditoria, Entrega, Evaluacion, Laboratorio, Rubrica, RubricaVersion
from tests.test_auth import ID_DOCENTE, ID_ESTUDIANTE
from tests.test_evaluaciones import ID_OTRO, MARCADOR, RUBRICA, auth, evaluar
from tests.test_revision_docente import accion, ajustar, editar, error


def listar(cliente, usuario=ID_DOCENTE, **params):
    return cliente.get("/api/evaluaciones", params=params, headers=auth(usuario))


def traza(cliente, evaluacion_id: int, usuario=ID_DOCENTE):
    return cliente.get(f"/api/evaluaciones/{evaluacion_id}/traza", headers=auth(usuario))


@pytest.fixture
def varias(datos) -> dict[str, int]:
    """Cinco evaluaciones con fechas, laboratorios, estudiantes y estados distintos."""
    with datos() as s:
        s.add(Laboratorio(id=11, cohorte_id=2, codigo="LAB02", titulo="Clases"))
        s.flush()
        s.add(Rubrica(id=2, laboratorio_id=11))
        s.flush()
        s.add(
            RubricaVersion(
                id=5, rubrica_id=2, version=1, contenido=copy.deepcopy(RUBRICA), estado="aprobada"
            )
        )
        s.flush()
        s.add(
            Entrega(
                id=3,
                estudiante_id=ID_ESTUDIANTE,
                laboratorio_id=11,
                rubrica_version_id=5,
                pdf_path="e3.pdf",
            )
        )
        s.flush()
        filas = [
            (101, 1, "borrador", "2026-11-10 08:00:00"),
            (102, 2, "en_revision", "2026-11-11 08:00:00"),
            (103, 3, "publicada", "2026-11-12 08:00:00"),
            (104, 1, "error", "2026-11-12 08:00:00"),
            (105, 3, "aprobada", "2026-11-13 08:00:00"),
        ]
        for eid, entrega, estado, fecha in filas:
            s.add(
                Evaluacion(
                    id=eid,
                    entrega_id=entrega,
                    estado=estado,
                    nota=Decimal("3.5") if estado != "error" else None,
                    respuesta_cruda={"crudo": MARCADOR},
                    resultado={"retroalimentacion_general": "texto"},
                    creada_en=datetime.fromisoformat(fecha),
                )
            )
        s.commit()
    return {"lab10": 10, "lab11": 11}


def ids(respuesta) -> list[int]:
    return [i["id"] for i in respuesta.json()["items"]]


# ---------- Listado ----------


def test_listado_orden_descendente_y_forma(cliente, varias):
    r = listar(cliente)
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == {"items", "total", "limit", "offset"}
    assert (cuerpo["total"], cuerpo["limit"], cuerpo["offset"]) == (5, 20, 0)
    # 103 y 104 tienen la misma fecha: desempate por id descendente.
    assert ids(r) == [105, 104, 103, 102, 101]
    item = cuerpo["items"][0]
    assert set(item) == {
        "id",
        "entrega_id",
        "estudiante",
        "laboratorio",
        "estado",
        "nota",
        "creada_en",
        "aprobada_en",
        "publicada_en",
    }
    assert item["estudiante"] == {"id": str(ID_ESTUDIANTE), "nombre": "Ana Estudiante"}
    assert item["laboratorio"] == {"id": 11, "codigo": "LAB02", "titulo": "Clases"}
    assert item["nota"] == 3.5
    assert item["creada_en"].endswith(("Z", "+00:00"))
    assert MARCADOR not in r.text
    assert "texto" not in r.text


def test_listado_vacio(cliente, datos):
    cuerpo = listar(cliente).json()
    assert cuerpo == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_filtro_por_laboratorio(cliente, varias):
    r = listar(cliente, laboratorio_id=11)
    assert ids(r) == [105, 103]
    assert r.json()["total"] == 2


def test_filtro_por_estado(cliente, varias):
    assert ids(listar(cliente, estado="en_revision")) == [102]
    assert ids(listar(cliente, estado="error")) == [104]


def test_filtro_por_estudiante(cliente, varias):
    assert ids(listar(cliente, estudiante_id=str(ID_OTRO))) == [102]
    assert ids(listar(cliente, estudiante_id=str(ID_ESTUDIANTE))) == [105, 104, 103, 101]


def test_filtros_combinados(cliente, varias):
    r = listar(cliente, laboratorio_id=10, estudiante_id=str(ID_ESTUDIANTE), estado="borrador")
    assert ids(r) == [101]


def test_paginacion(cliente, varias):
    r = listar(cliente, limit=2, offset=1)
    assert ids(r) == [104, 103]
    assert (r.json()["total"], r.json()["limit"], r.json()["offset"]) == (5, 2, 1)
    assert ids(listar(cliente, limit=2, offset=4)) == [101]
    assert ids(listar(cliente, limit=2, offset=10)) == []


def test_tope_de_limit(cliente, varias):
    assert listar(cliente, limit=100).status_code == 200
    detalle = error(listar(cliente, limit=101), 422)
    assert "limit" in detalle and "100" in detalle


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": -1},
        {"offset": -1},
        {"limit": "abc"},
        {"estudiante_id": "no-es-uuid"},
        {"laboratorio_id": "x"},
    ],
)
def test_parametros_invalidos_422(cliente, varias, params):
    detalle = error(listar(cliente, **params), 422)
    assert "Datos de entrada no válidos" in detalle
    assert "Input should" not in detalle


def test_estado_invalido_422(cliente, varias):
    detalle = error(listar(cliente, estado="inventado"), 422)
    assert "'inventado'" in detalle
    assert "borrador" in detalle


# ---------- Traza ----------


@pytest.fixture
def recorrida(cliente) -> int:
    """Evaluación que pasa por todo el ciclo HITL."""
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    accion(cliente, evaluacion_id, "revisar")
    ajustar(cliente, evaluacion_id, "C2", {"nivel_final": "Bajo", "motivo": "Confuso"})
    editar(cliente, evaluacion_id, {"retroalimentacion_general": "Editado", "motivo": "Tono"})
    accion(cliente, evaluacion_id, "aprobar")
    accion(cliente, evaluacion_id, "publicar")
    return evaluacion_id


def test_traza_completa_en_orden(cliente, recorrida):
    r = traza(cliente, recorrida)
    assert r.status_code == 200
    cuerpo = r.json()
    acciones = [e["accion"] for e in cuerpo["eventos"]]
    assert acciones == [
        "lanzar_evaluacion",
        "evaluacion_ia",
        "pasar_a_revision",
        "ajustar_criterio",
        "editar_retroalimentacion",
        "aprobar",
        "publicar",
    ]
    assert cuerpo["evaluacion_id"] == recorrida
    assert cuerpo["estado"] == "publicada"
    assert cuerpo["nota"] == 2.3
    assert cuerpo["proveedor"] == "gemini"
    assert cuerpo["modelo"] == "modelo-de-prueba"
    assert cuerpo["temperatura"] == pytest.approx(0.1)
    assert cuerpo["prompt_version"] == "1.0"
    assert (cuerpo["rubrica_version_id"], cuerpo["rubrica_version"]) == (1, 1)


def test_traza_fechas_iso_utc_y_usuario(cliente, recorrida):
    eventos = traza(cliente, recorrida).json()["eventos"]
    for evento in eventos:
        assert evento["fecha"].endswith(("Z", "+00:00")), evento["fecha"]
        datetime.fromisoformat(evento["fecha"].replace("Z", "+00:00"))
    ajuste = next(e for e in eventos if e["accion"] == "ajustar_criterio")
    assert ajuste["usuario"] == {"id": str(ID_DOCENTE), "nombre": "Diego Docente"}
    assert ajuste["motivo"] == "Confuso"
    assert ajuste["antes"]["nivel_final"] == "Alto"
    assert ajuste["despues"]["nivel_final"] == "Bajo"


def test_traza_incluye_respuestas_crudas_para_docente(cliente, recorrida):
    r = traza(cliente, recorrida)
    assert MARCADOR in r.text
    ia = next(e for e in r.json()["eventos"] if e["accion"] == "evaluacion_ia")
    assert MARCADOR in repr(ia["despues"]["respuestas_crudas"])


def test_traza_incluye_errores_de_ia(cliente, datos, evaluador):
    evaluador.excepcion = RuntimeError("fallo del proveedor")
    evaluacion_id = evaluar(cliente).json()["evaluacion_id"]
    acciones = [e["accion"] for e in traza(cliente, evaluacion_id).json()["eventos"]]
    assert acciones == ["lanzar_evaluacion", "evaluacion_ia_error"]
    assert traza(cliente, evaluacion_id).json()["estado"] == "error"


def test_traza_orden_por_fecha_y_desempate_por_id(cliente, datos, recorrida):
    with datos() as s:
        s.add(
            Auditoria(
                id=900,
                entidad="evaluaciones",
                entidad_id=str(recorrida),
                accion="antiguo",
                creado_en=datetime(2020, 1, 1),
            )
        )
        s.commit()
    acciones = [e["accion"] for e in traza(cliente, recorrida).json()["eventos"]]
    assert acciones[0] == "antiguo"
    assert acciones[1:3] == ["lanzar_evaluacion", "evaluacion_ia"]


def test_traza_filtra_claves_secretas(cliente, datos, recorrida):
    with datos() as s:
        s.add(
            Auditoria(
                entidad="evaluaciones",
                entidad_id=str(recorrida),
                accion="prueba_secretos",
                antes={"api_key": "SK_FILTRAR_1", "visible": "se ve"},
                despues={
                    "anidado": {"token": "SK_FILTRAR_2", "Password": "SK_FILTRAR_3"},
                    "lista": [{"database_url": "SK_FILTRAR_4", "ok": 1}],
                    "Authorization": "Bearer SK_FILTRAR_5",
                    "secret_value": "SK_FILTRAR_6",
                    "openai_key": "SK_FILTRAR_7",
                },
            )
        )
        s.commit()
    r = traza(cliente, recorrida)
    assert r.status_code == 200
    assert "SK_FILTRAR" not in r.text
    evento = next(e for e in r.json()["eventos"] if e["accion"] == "prueba_secretos")
    assert evento["antes"] == {"visible": "se ve"}
    assert evento["despues"] == {"anidado": {}, "lista": [{"ok": 1}]}


def test_traza_solo_eventos_de_esa_evaluacion(cliente, datos, recorrida):
    with datos() as s:
        s.add(Auditoria(entidad="evaluaciones", entidad_id="999999", accion="ajena"))
        s.add(Auditoria(entidad="perfiles", entidad_id=str(recorrida), accion="otra_entidad"))
        s.commit()
    acciones = [e["accion"] for e in traza(cliente, recorrida).json()["eventos"]]
    assert "ajena" not in acciones
    assert "otra_entidad" not in acciones


def test_traza_estudiante_403_incluso_publicada(cliente, recorrida):
    error(traza(cliente, recorrida, ID_ESTUDIANTE), 403)


def test_lanzamiento_registrado_en_auditoria(cliente, recorrida):
    evento = traza(cliente, recorrida).json()["eventos"][0]
    assert evento["accion"] == "lanzar_evaluacion"
    assert evento["usuario"]["id"] == str(ID_DOCENTE)
    assert evento["despues"]["estado"] == "procesando"
    assert evento["despues"]["entrega_id"] == 1
