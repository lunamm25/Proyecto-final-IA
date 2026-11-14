"""Pruebas de la revisión docente (RF-07): transiciones, ajustes, edición, aprobar y publicar.

La evaluación de partida se crea con el flujo real (POST /evaluar con evaluador falso) y queda en
`borrador` con C1 = "Bueno" y C2 = "Alto" → nota 4,3 (ver tests/test_evaluaciones.py).
"""

import copy
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Auditoria, EvaluacionCriterio, RubricaVersion
from app.services import revision
from app.services.nota import calcular_nota
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE
from tests.test_evaluaciones import (
    RUBRICA,
    auditorias,
    auth,
    criterios_de,
    evaluar,
    leer,
    poner_estado,
)

MSG_PENDIENTE = "La evaluación está pendiente de revisión docente."


@pytest.fixture
def ev(cliente, datos) -> int:
    """Id de una evaluación en `borrador` creada con el flujo real."""
    respuesta = evaluar(cliente)
    assert respuesta.status_code == 202
    evaluacion_id = respuesta.json()["evaluacion_id"]
    assert leer(datos, evaluacion_id).estado == "borrador"
    return evaluacion_id


def accion(cliente, evaluacion_id: int, nombre: str, usuario=ID_DOCENTE):
    return cliente.post(f"/api/evaluaciones/{evaluacion_id}/{nombre}", headers=auth(usuario))


def ajustar(cliente, evaluacion_id: int, cid: str, cuerpo, usuario=ID_DOCENTE):
    return cliente.patch(
        f"/api/evaluaciones/{evaluacion_id}/criterios/{cid}", json=cuerpo, headers=auth(usuario)
    )


def editar(cliente, evaluacion_id: int, cuerpo, usuario=ID_DOCENTE):
    return cliente.patch(
        f"/api/evaluaciones/{evaluacion_id}/retroalimentacion", json=cuerpo, headers=auth(usuario)
    )


def ver(cliente, evaluacion_id: int, usuario=ID_DOCENTE):
    return cliente.get(f"/api/evaluaciones/{evaluacion_id}", headers=auth(usuario))


def error(respuesta, codigo: int) -> str:
    """Comprueba el código y la forma {"detail": "<texto>"}; devuelve el texto."""
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"detail"}
    assert isinstance(cuerpo["detail"], str) and cuerpo["detail"]
    return cuerpo["detail"]


def fila(fabrica, evaluacion_id: int, cid: str) -> EvaluacionCriterio:
    return next(f for f in criterios_de(fabrica, evaluacion_id) if f.criterio_id == cid)


def de_accion(fabrica, evaluacion_id: int, nombre: str) -> list[Auditoria]:
    return [a for a in auditorias(fabrica, evaluacion_id) if a.accion == nombre]


# ---------- Permisos en todos los endpoints nuevos ----------

ENDPOINTS = [
    ("post", "/api/evaluaciones/{id}/revisar", None),
    ("patch", "/api/evaluaciones/{id}/criterios/C1", {"nivel_final": "Excelente", "motivo": "x"}),
    ("patch", "/api/evaluaciones/{id}/retroalimentacion", {"retroalimentacion_general": "Hola"}),
    ("post", "/api/evaluaciones/{id}/aprobar", None),
    ("post", "/api/evaluaciones/{id}/publicar", None),
    ("get", "/api/evaluaciones/{id}/traza", None),
    ("get", "/api/evaluaciones", None),
]


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS)
def test_sin_token_401(cliente, ev, metodo, ruta, cuerpo):
    respuesta = cliente.request(metodo, ruta.format(id=ev), json=cuerpo)
    error(respuesta, 401)


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS)
def test_estudiante_403(cliente, datos, ev, metodo, ruta, cuerpo):
    respuesta = cliente.request(
        metodo, ruta.format(id=ev), json=cuerpo, headers=auth(ID_ESTUDIANTE)
    )
    error(respuesta, 403)
    assert leer(datos, ev).estado == "borrador"
    assert fila(datos, ev, "C1").nivel_final == "Bueno"


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"), [e for e in ENDPOINTS if e[1] != "/api/evaluaciones"]
)
def test_evaluacion_inexistente_404(cliente, ev, metodo, ruta, cuerpo):
    respuesta = cliente.request(metodo, ruta.format(id=999), json=cuerpo, headers=auth(ID_DOCENTE))
    error(respuesta, 404)


@pytest.mark.parametrize("usuario", [ID_DOCENTE, ID_ADMIN])
def test_flujo_completo_docente_y_admin(cliente, datos, ev, usuario):
    assert accion(cliente, ev, "revisar", usuario).status_code == 200
    r = ajustar(cliente, ev, "C1", {"nivel_final": "Excelente", "motivo": "Muy completo"}, usuario)
    assert r.status_code == 200
    assert editar(cliente, ev, {"retroalimentacion_general": "Bien"}, usuario).status_code == 200
    assert accion(cliente, ev, "aprobar", usuario).status_code == 200
    assert accion(cliente, ev, "publicar", usuario).status_code == 200
    assert cliente.get(f"/api/evaluaciones/{ev}/traza", headers=auth(usuario)).status_code == 200
    assert cliente.get("/api/evaluaciones", headers=auth(usuario)).status_code == 200
    assert leer(datos, ev).estado == "publicada"


# ---------- Transiciones ----------


def test_transiciones_validas_en_orden(cliente, datos, ev):
    r = accion(cliente, ev, "revisar")
    assert r.status_code == 200
    assert r.json()["estado"] == "en_revision"
    r = accion(cliente, ev, "aprobar")
    assert r.status_code == 200
    assert r.json()["estado"] == "aprobada"
    r = accion(cliente, ev, "publicar")
    assert r.status_code == 200
    assert r.json()["estado"] == "publicada"
    acciones = [a.accion for a in auditorias(datos, ev)]
    for nombre in ("pasar_a_revision", "aprobar", "publicar"):
        assert acciones.count(nombre) == 1


@pytest.mark.parametrize(
    ("estado", "nombre"),
    [
        ("borrador", "aprobar"),
        ("borrador", "publicar"),
        ("en_revision", "publicar"),
        ("en_revision", "revisar"),
        ("aprobada", "revisar"),
        ("aprobada", "aprobar"),
        ("publicada", "revisar"),
        ("publicada", "aprobar"),
        ("publicada", "publicar"),
        ("error", "revisar"),
        ("error", "aprobar"),
        ("error", "publicar"),
        ("procesando", "revisar"),
        ("procesando", "aprobar"),
        ("procesando", "publicar"),
    ],
)
def test_transiciones_invalidas_409(cliente, datos, ev, estado, nombre):
    poner_estado(datos, ev, estado)
    antes = len(auditorias(datos, ev))
    detalle = error(accion(cliente, ev, nombre), 409)
    assert f"'{estado}'" in detalle
    assert leer(datos, ev).estado == estado
    assert len(auditorias(datos, ev)) == antes


def test_mensaje_de_paso_a_revision(cliente, datos, ev):
    poner_estado(datos, ev, "aprobada")
    detalle = error(accion(cliente, ev, "revisar"), 409)
    assert detalle == "No se puede pasar a revisión una evaluación en estado 'aprobada'."


def test_auditoria_paso_a_revision(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    (registro,) = de_accion(datos, ev, "pasar_a_revision")
    assert registro.usuario_id == ID_DOCENTE
    assert registro.antes == {"estado": "borrador"}
    assert registro.despues == {"estado": "en_revision"}


# ---------- Ajustar criterio ----------


def test_ajuste_recalcula_nota_con_nota_py(cliente, datos, ev):
    # Rúbrica v1: C1 (60 %) niveles 5/4/1 → "Bueno" normaliza (4-1)/(5-1) = 0,75;
    # C2 (40 %) niveles 3/0 → "Bajo" normaliza 0. Nota = 0,6·0,75·5 + 0,4·0·5 = 2,25 → 2,3.
    r = ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "El informe es confuso"})
    assert r.status_code == 200
    esperado = calcular_nota(RUBRICA["criterios"], {"C1": "Bueno", "C2": "Bajo"})
    assert esperado.nota == Decimal("2.3")
    assert r.json()["nota"] == 2.3
    assert leer(datos, ev).nota == Decimal("2.3")
    c2 = fila(datos, ev, "C2")
    assert c2.nivel_final == "Bajo"
    assert c2.nivel_ia == "Alto"
    assert c2.puntaje_normalizado == pytest.approx(0.0)
    assert c2.ajuste_docente == "El informe es confuso"
    assert fila(datos, ev, "C1").puntaje_normalizado == pytest.approx(0.75)


def test_ajuste_a_todo_maximo_da_5(cliente, datos, ev):
    # C1 "Excelente" = 1 y C2 "Alto" = 1 → 0,6·5 + 0,4·5 = 5,0.
    r = ajustar(cliente, ev, "C1", {"nivel_final": "Excelente", "motivo": "Muy completo"})
    assert r.json()["nota"] == 5.0
    assert fila(datos, ev, "C1").puntaje_normalizado == pytest.approx(1.0)


def test_ajuste_en_revision_permitido(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    r = ajustar(cliente, ev, "C1", {"nivel_final": "Insuficiente", "motivo": "No funciona"})
    assert r.status_code == 200
    # C1 = 0 y C2 = 1 → 0,4·5 = 2,0.
    assert leer(datos, ev).nota == Decimal("2.0")
    assert leer(datos, ev).estado == "en_revision"


def test_campo_nota_en_el_cuerpo_no_tiene_efecto(cliente, datos, ev):
    cuerpo = {"nivel_final": "Bajo", "motivo": "Confuso", "nota": 5.0}
    r = ajustar(cliente, ev, "C2", cuerpo)
    assert r.status_code == 200
    assert leer(datos, ev).nota == Decimal("2.3")


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"nivel_final": "Bajo"},
        {"nivel_final": "Bajo", "motivo": ""},
        {"nivel_final": "Bajo", "motivo": "    "},
        {"nivel_final": "Bajo", "motivo": None},
        {"nivel_final": "Bajo", "motivo": "x" * 1001},
        {"motivo": "Sin nivel"},
    ],
)
def test_ajuste_cuerpo_invalido_422(cliente, datos, ev, cuerpo):
    detalle = error(ajustar(cliente, ev, "C2", cuerpo), 422)
    assert "Datos de entrada no válidos" in detalle
    assert fila(datos, ev, "C2").nivel_final == "Alto"
    assert leer(datos, ev).nota == Decimal("4.3")


def test_motivo_vacio_mensaje_en_espanol(cliente, ev):
    detalle = error(ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "  "}), 422)
    assert "motivo" in detalle and "vacío" in detalle


def test_nivel_inexistente_422(cliente, datos, ev):
    detalle = error(ajustar(cliente, ev, "C1", {"nivel_final": "Mágico", "motivo": "x"}), 422)
    assert detalle == "El nivel 'Mágico' no existe en el criterio 'C1'."
    assert leer(datos, ev).nota == Decimal("4.3")


def test_nivel_de_otro_criterio_422(cliente, ev):
    error(ajustar(cliente, ev, "C1", {"nivel_final": "Alto", "motivo": "x"}), 422)


def test_criterio_inexistente_404(cliente, ev):
    detalle = error(ajustar(cliente, ev, "C99", {"nivel_final": "Alto", "motivo": "x"}), 404)
    assert "C99" in detalle


@pytest.mark.parametrize("estado", ["aprobada", "publicada", "error", "procesando"])
def test_ajuste_fuera_de_revision_409(cliente, datos, ev, estado):
    poner_estado(datos, ev, estado)
    detalle = error(ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "x"}), 409)
    assert f"'{estado}'" in detalle
    assert fila(datos, ev, "C2").nivel_final == "Alto"


def test_ajuste_tras_aprobar_por_api_409(cliente, ev):
    accion(cliente, ev, "revisar")
    accion(cliente, ev, "aprobar")
    error(ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "x"}), 409)
    accion(cliente, ev, "publicar")
    error(ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "x"}), 409)


def test_ajuste_usa_la_version_de_la_entrega_no_la_vigente(cliente, datos, ev):
    nueva = copy.deepcopy(RUBRICA)
    nueva["criterios"][0]["niveles"][0]["nombre"] = "Sobresaliente"
    nueva["criterios"][0]["ponderacion"] = 90
    nueva["criterios"][1]["ponderacion"] = 10
    with datos() as s:
        s.add(RubricaVersion(id=2, rubrica_id=1, version=2, contenido=nueva, estado="aprobada"))
        s.commit()
    error(ajustar(cliente, ev, "C1", {"nivel_final": "Sobresaliente", "motivo": "x"}), 422)
    r = ajustar(cliente, ev, "C1", {"nivel_final": "Excelente", "motivo": "x"})
    assert r.status_code == 200
    # Con la v1 (60/40): 0,6·1·5 + 0,4·1·5 = 5,0. (Con la v2 no existiría "Excelente".)
    assert r.json()["nota"] == 5.0
    assert r.json()["rubrica_version"] == 1


def test_auditoria_del_ajuste(cliente, datos, ev):
    ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "  El informe es confuso  "})
    (registro,) = de_accion(datos, ev, "ajustar_criterio")
    assert registro.usuario_id == ID_DOCENTE
    assert registro.entidad == "evaluaciones"
    assert registro.entidad_id == str(ev)
    assert registro.antes == {"criterio_id": "C2", "nivel_final": "Alto", "nota": 4.3}
    assert registro.despues == {"criterio_id": "C2", "nivel_final": "Bajo", "nota": 2.3}
    assert registro.motivo == "El informe es confuso"
    assert registro.creado_en is not None


def test_ajuste_al_mismo_nivel_no_cambia_ni_audita(cliente, datos, ev):
    r = ajustar(cliente, ev, "C2", {"nivel_final": "Alto", "motivo": "Confirmo el nivel"})
    assert r.status_code == 200
    assert r.json()["nota"] == 4.3
    assert de_accion(datos, ev, "ajustar_criterio") == []
    assert fila(datos, ev, "C2").ajuste_docente is None


def test_vista_docente_muestra_nivel_ia_y_ajuste(cliente, ev):
    ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "Confuso"})
    c2 = next(c for c in ver(cliente, ev).json()["criterios"] if c["criterio_id"] == "C2")
    assert c2["nivel_ia"] == "Alto"
    assert c2["nivel_final"] == "Bajo"
    assert c2["ajuste_docente"] == "Confuso"


# ---------- Atomicidad ----------


def test_fallo_al_auditar_no_deja_el_cambio(cliente, datos, ev, monkeypatch):
    original = revision._auditar

    def _auditar_roto(db, *args, **kwargs):
        original(db, *args, **kwargs)
        db.add(Auditoria(entidad="evaluaciones", entidad_id=str(ev), accion=None))

    monkeypatch.setattr(revision, "_auditar", _auditar_roto)
    sin_excepciones = TestClient(cliente.app, raise_server_exceptions=False)
    r = ajustar(sin_excepciones, ev, "C2", {"nivel_final": "Bajo", "motivo": "Confuso"})
    assert r.status_code == 500
    assert leer(datos, ev).nota == Decimal("4.3")
    c2 = fila(datos, ev, "C2")
    assert (c2.nivel_final, c2.ajuste_docente) == ("Alto", None)
    assert de_accion(datos, ev, "ajustar_criterio") == []


def test_fallo_al_auditar_no_cambia_el_estado(cliente, datos, ev, monkeypatch):
    def _auditar_roto(*_args, **_kwargs):
        raise RuntimeError("fallo simulado al escribir auditoría")

    monkeypatch.setattr(revision, "_auditar", _auditar_roto)
    sin_excepciones = TestClient(cliente.app, raise_server_exceptions=False)
    assert accion(sin_excepciones, ev, "revisar").status_code == 500
    assert leer(datos, ev).estado == "borrador"


# ---------- Editar retroalimentación ----------

EDICION = {
    "retroalimentacion_general": "Buen trabajo; revisa las pruebas.",
    "aspectos_a_fortalecer": ["Pruebas unitarias", "Documentación"],
    "criterios": [
        {
            "criterio_id": "C1",
            "justificacion": "Código claro y funcional.",
            "recomendacion": "Agrega pruebas con pytest.",
        }
    ],
    "motivo": "Tono más cercano",
}


def test_edicion_conserva_el_original_de_la_ia(cliente, datos, ev):
    r = editar(cliente, ev, EDICION)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (
        cuerpo["retroalimentacion"]["retroalimentacion_general"]
        == EDICION["retroalimentacion_general"]
    )
    assert cuerpo["retroalimentacion"]["aspectos_a_fortalecer"] == EDICION["aspectos_a_fortalecer"]
    assert cuerpo["retroalimentacion"]["aprendizajes_identificados"] == ["Funciones"]
    assert cuerpo["retroalimentacion_ia"]["retroalimentacion_general"] == "Buen trabajo"
    assert cuerpo["retroalimentacion_ia"]["aspectos_a_fortalecer"] == ["Pruebas"]
    c1 = next(c for c in cuerpo["criterios"] if c["criterio_id"] == "C1")
    assert c1["justificacion"] == "Código claro y funcional."
    assert c1["recomendacion"] == "Agrega pruebas con pytest."
    assert c1["fortalezas"] == ["Ordenado"]
    assert c1["original_ia"]["justificacion"] == "Justificación de C1"
    assert c1["original_ia"]["recomendacion"] == "Agregar tests"
    # En la BD sigue intacto lo de la IA.
    guardada = leer(datos, ev)
    assert guardada.resultado["retroalimentacion_general"] == "Buen trabajo"
    assert guardada.resultado["criterios"][0]["recomendacion"] == "Agregar tests"
    assert fila(datos, ev, "C1").justificacion == "Justificación de C1"
    assert guardada.estado == "borrador"
    assert guardada.nota == Decimal("4.3")


def test_edicion_se_ve_en_el_get_del_docente(cliente, ev):
    editar(cliente, ev, EDICION)
    cuerpo = ver(cliente, ev).json()
    assert (
        cuerpo["retroalimentacion"]["retroalimentacion_general"]
        == EDICION["retroalimentacion_general"]
    )
    assert cuerpo["retroalimentacion_ia"]["retroalimentacion_general"] == "Buen trabajo"


def test_auditoria_de_la_edicion(cliente, datos, ev):
    editar(cliente, ev, EDICION)
    (registro,) = de_accion(datos, ev, "editar_retroalimentacion")
    assert registro.usuario_id == ID_DOCENTE
    assert registro.motivo == "Tono más cercano"
    assert registro.antes["general"]["retroalimentacion_general"] == "Buen trabajo"
    assert (
        registro.despues["general"]["retroalimentacion_general"]
        == EDICION["retroalimentacion_general"]
    )
    assert registro.antes["criterios"]["C1"]["justificacion"] == "Justificación de C1"
    assert registro.despues["criterios"]["C1"]["recomendacion"] == "Agrega pruebas con pytest."
    assert "fortalezas" not in registro.despues["criterios"]["C1"]


def test_edicion_sin_motivo_es_valida(cliente, datos, ev):
    r = editar(cliente, ev, {"retroalimentacion_general": "Nuevo texto"})
    assert r.status_code == 200
    (registro,) = de_accion(datos, ev, "editar_retroalimentacion")
    assert registro.motivo is None


def test_null_vuelve_al_texto_de_la_ia(cliente, datos, ev):
    editar(cliente, ev, EDICION)
    restaurar = {
        "retroalimentacion_general": None,
        "criterios": [{"criterio_id": "C1", "justificacion": None}],
    }
    r = editar(cliente, ev, restaurar)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["retroalimentacion"]["retroalimentacion_general"] == "Buen trabajo"
    c1 = next(c for c in cuerpo["criterios"] if c["criterio_id"] == "C1")
    assert c1["justificacion"] == "Justificación de C1"
    assert c1["recomendacion"] == "Agrega pruebas con pytest."
    assert len(de_accion(datos, ev, "editar_retroalimentacion")) == 2


def test_edicion_sin_cambios_no_audita(cliente, datos, ev):
    r = editar(cliente, ev, {"retroalimentacion_general": "Buen trabajo"})
    assert r.status_code == 200
    assert de_accion(datos, ev, "editar_retroalimentacion") == []


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"retroalimentacion_general": ""},
        {"retroalimentacion_general": "   "},
        {"criterios": [{"criterio_id": "C1", "justificacion": ""}]},
        {"aspectos_a_fortalecer": ["ok", "  "]},
        {"retroalimentacion_general": "x" * 5001},
        {},
        {"motivo": "solo motivo"},
        {"criterios": [{"criterio_id": "C1"}]},
    ],
)
def test_edicion_invalida_422(cliente, datos, ev, cuerpo):
    error(editar(cliente, ev, cuerpo), 422)
    assert de_accion(datos, ev, "editar_retroalimentacion") == []


def test_edicion_criterio_repetido_422(cliente, ev):
    cuerpo = {
        "criterios": [
            {"criterio_id": "C1", "justificacion": "a"},
            {"criterio_id": "C1", "justificacion": "b"},
        ]
    }
    error(editar(cliente, ev, cuerpo), 422)


def test_edicion_criterio_inexistente_404(cliente, ev):
    cuerpo = {"criterios": [{"criterio_id": "C99", "justificacion": "a"}]}
    assert "C99" in error(editar(cliente, ev, cuerpo), 404)


@pytest.mark.parametrize("estado", ["aprobada", "publicada", "error", "procesando"])
def test_edicion_fuera_de_revision_409(cliente, datos, ev, estado):
    poner_estado(datos, ev, estado)
    detalle = error(editar(cliente, ev, {"retroalimentacion_general": "Nuevo"}), 409)
    assert f"'{estado}'" in detalle


def test_edicion_en_revision_permitida_y_tras_aprobar_409(cliente, ev):
    accion(cliente, ev, "revisar")
    assert editar(cliente, ev, {"retroalimentacion_general": "Nuevo"}).status_code == 200
    accion(cliente, ev, "aprobar")
    error(editar(cliente, ev, {"retroalimentacion_general": "Otro"}), 409)


# ---------- Aprobar ----------


def test_aprobar_guarda_quien_y_cuando(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    r = accion(cliente, ev, "aprobar")
    assert r.status_code == 200
    assert r.json()["aprobada_en"] is not None
    guardada = leer(datos, ev)
    assert guardada.aprobada_por == ID_DOCENTE
    assert isinstance(guardada.aprobada_en, datetime)
    (registro,) = de_accion(datos, ev, "aprobar")
    assert registro.antes["estado"] == "en_revision"
    assert registro.despues["estado"] == "aprobada"
    assert registro.despues["nota"] == 4.3


def test_aprobar_con_criterio_sin_nivel_final_409(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    with datos() as s:
        f = s.scalar(
            select(EvaluacionCriterio).where(
                EvaluacionCriterio.evaluacion_id == ev, EvaluacionCriterio.criterio_id == "C2"
            )
        )
        f.nivel_final = None
        s.commit()
    detalle = error(accion(cliente, ev, "aprobar"), 409)
    assert "C2" in detalle
    assert leer(datos, ev).estado == "en_revision"


def test_aprobar_con_criterio_faltante_409(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    with datos() as s:
        f = s.scalar(
            select(EvaluacionCriterio).where(
                EvaluacionCriterio.evaluacion_id == ev, EvaluacionCriterio.criterio_id == "C2"
            )
        )
        s.delete(f)
        s.commit()
    assert "C2" in error(accion(cliente, ev, "aprobar"), 409)


def test_aprobar_con_rubrica_que_ya_no_valida_409(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    rota = copy.deepcopy(RUBRICA)
    rota["criterios"][1]["ponderacion"] = 30  # suma 90 %
    with datos() as s:
        s.get(RubricaVersion, 1).contenido = rota
        s.commit()
    detalle = error(accion(cliente, ev, "aprobar"), 409)
    assert "rúbrica" in detalle
    assert leer(datos, ev).estado == "en_revision"
    assert leer(datos, ev).aprobada_en is None


def test_aprobar_recalcula_nota_si_no_coincide(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    with datos() as s:
        from app.models import Evaluacion

        s.get(Evaluacion, ev).nota = Decimal("1.0")
        s.commit()
    r = accion(cliente, ev, "aprobar")
    assert r.status_code == 200
    assert r.json()["nota"] == 4.3
    (registro,) = de_accion(datos, ev, "aprobar")
    assert registro.antes["nota"] == 1.0
    assert registro.despues["nota"] == 4.3
    assert registro.despues["nota_recalculada"] is True


# ---------- Publicar y vista del estudiante ----------


def test_publicar_guarda_fecha(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    accion(cliente, ev, "aprobar")
    r = accion(cliente, ev, "publicar")
    assert r.status_code == 200
    assert r.json()["publicada_en"] is not None
    assert isinstance(leer(datos, ev).publicada_en, datetime)
    (registro,) = de_accion(datos, ev, "publicar")
    assert registro.usuario_id == ID_DOCENTE


def test_publicar_sin_aprobar_409(cliente, datos, ev):
    accion(cliente, ev, "revisar")
    assert "'en_revision'" in error(accion(cliente, ev, "publicar"), 409)
    assert leer(datos, ev).publicada_en is None


CAMPOS_INTERNOS = ("proveedor", "modelo", "temperatura", "prompt_version", "retroalimentacion_ia")


def test_estudiante_solo_ve_publicada_con_lo_final(cliente, ev):
    editar(cliente, ev, EDICION)
    ajustar(cliente, ev, "C2", {"nivel_final": "Bajo", "motivo": "MOTIVO_INTERNO"})
    for nombre in ("revisar", "aprobar"):
        accion(cliente, ev, nombre)
        assert error(ver(cliente, ev, ID_ESTUDIANTE), 403) == MSG_PENDIENTE
    accion(cliente, ev, "publicar")
    r = ver(cliente, ev, ID_ESTUDIANTE)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "publicada"
    assert cuerpo["nota"] == 2.3
    assert (
        cuerpo["retroalimentacion"]["retroalimentacion_general"]
        == EDICION["retroalimentacion_general"]
    )
    for campo in CAMPOS_INTERNOS:
        assert cuerpo.get(campo) is None
    c1, c2 = cuerpo["criterios"]
    assert c1["justificacion"] == "Código claro y funcional."
    assert c2["nivel_final"] == "Bajo"
    for c in (c1, c2):
        assert c["nivel_ia"] is None
        assert c["ajuste_docente"] is None
        assert c["original_ia"] is None
    assert "MOTIVO_INTERNO" not in r.text
    assert "Justificación de C1" not in r.text
    assert c1["recomendacion"] == "Agrega pruebas con pytest."
    assert c2["recomendacion"] == "Agregar tests"  # C2 no se editó: texto de la IA
    assert "modelo-de-prueba" not in r.text


def test_estudiante_sin_edicion_ve_texto_de_la_ia(cliente, ev):
    for nombre in ("revisar", "aprobar", "publicar"):
        accion(cliente, ev, nombre)
    cuerpo = ver(cliente, ev, ID_ESTUDIANTE).json()
    assert cuerpo["retroalimentacion"]["retroalimentacion_general"] == "Buen trabajo"
    assert cuerpo["criterios"][0]["justificacion"] == "Justificación de C1"
