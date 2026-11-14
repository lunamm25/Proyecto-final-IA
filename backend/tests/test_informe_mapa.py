"""Pruebas de RF-08 y RF-09: listado de estudiantes, informe integrado y mapa de conocimiento.

Nunca se usa la IA real ni la red: se inyecta una IA falsa con `obtener_ia_informe`. Los tests no
importan `app.ia.informe` ni `app.ia.tematicas`. Todos los números los calcula el backend; la IA
falsa devuelve números raros a propósito para comprobar que no se usan.

Escenario del estudiante principal (ID_EST), rúbrica con C1 (50 %, niveles 5/4/3/1) y
C2 (50 %, niveles 3/2/0):
    C1-01  Bueno/Medio      → 0,5·0,75·5 + 0,5·(2/3)·5 = 1,875 + 1,6667 = 3,54 → 3,5
    C1-02  Regular/Alto     → 0,5·0,5·5  + 0,5·1·5     = 1,25 + 2,5     = 3,75 → 3,8
    C2-01  Excelente/Alto   → 5,0
    C2-02  Bueno/Alto       → 1,875 + 2,5 = 4,375 → 4,4  (publicada más reciente; hay otra
                               publicada ANTES con nota 0,0 que no cuenta)
    C1-03  solo una evaluación `aprobada` → no cuenta.
"""

import copy
import json
import sys
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api.deps import obtener_ia_informe
from app.models import (
    Auditoria,
    Entrega,
    Evaluacion,
    EvaluacionCriterio,
    Laboratorio,
    Perfil,
    Rubrica,
    RubricaVersion,
    Tematica,
)
from app.services.desempeno import nivel_dominio
from app.services.informe_ia import (
    AccionPlanIA,
    GeneracionIAError,
    IAInformeReal,
    MapeoCriterioIA,
    MapeoIA,
    NarrativaIA,
    traducir_mapeo,
    traducir_narrativa,
)
from app.services.nota import calcular_nota
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE
from tests.test_evaluaciones import auth

ID_EST = uuid.UUID("7e57a1b2-c3d4-4e5f-8a9b-0c1d2e3f4a5b")
ID_BETO = uuid.UUID("b0b0b0b0-0000-4000-8000-000000000001")
ID_SIN_NOMBRE = uuid.UUID("c0c0c0c0-0000-4000-8000-000000000002")
NOMBRE_MARCA = "Zulema MARCANOMBREQX"
CORREO_MARCA = "marca.correo.qx@ejemplo.edu"
T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)

RUBRICA = {
    "titulo": "Rúbrica informe",
    "criterios": [
        {
            "id": "C1",
            "competencia": "Programación",
            "nombre": "Código",
            "ponderacion": 50,
            "niveles": [
                {"nombre": "Excelente", "puntaje": 5, "descriptor": "a"},
                {"nombre": "Bueno", "puntaje": 4, "descriptor": "b"},
                {"nombre": "Regular", "puntaje": 3, "descriptor": "c"},
                {"nombre": "Insuficiente", "puntaje": 1, "descriptor": "d"},
            ],
        },
        {
            "id": "C2",
            "competencia": "Comunicación",
            "nombre": "Informe escrito",
            "ponderacion": 50,
            "niveles": [
                {"nombre": "Alto", "puntaje": 3, "descriptor": "a"},
                {"nombre": "Medio", "puntaje": 2, "descriptor": "b"},
                {"nombre": "Bajo", "puntaje": 0, "descriptor": "c"},
            ],
        },
    ],
}

# Laboratorios creados a propósito en desorden (el id no sigue el orden cronológico).
LABS = {"C2-01": (21, 2), "C1-02": (22, 1), "C1-01": (23, 1), "C2-02": (24, 2), "C1-03": (25, 1)}
TEMATICAS = [(1, "Aprendizaje automático", None), (2, "Ética y verificación", None)]
SUBTEMA = (3, "Redes neuronales", 1)

ROUTES = ["/api/estudiantes", "/api/estudiantes/{id}/informe", "/api/estudiantes/{id}/mapa"]


# ---------- Datos de prueba ----------


def _evaluacion(
    s,
    estudiante: uuid.UUID,
    codigo: str,
    niveles: dict[str, str],
    estado: str = "publicada",
    publicada_en: datetime | None = None,
    marca: str = "",
) -> int:
    """Crea entrega + evaluación + criterios (nota calculada con nota.py); devuelve el id."""
    lab_id = LABS[codigo][0]
    entrega = Entrega(
        estudiante_id=estudiante, laboratorio_id=lab_id, rubrica_version_id=lab_id, pdf_path="x"
    )
    s.add(entrega)
    s.flush()
    resultado = calcular_nota(RUBRICA["criterios"], niveles)
    evaluacion = Evaluacion(
        entrega_id=entrega.id,
        estado=estado,
        nota=None if estado == "error" else resultado.nota,
        publicada_en=publicada_en,
        resultado={
            "criterios": [
                {
                    "criterio_id": cid,
                    "nivel_elegido": nivel,
                    "fortalezas": [f"{marca}Fortaleza {codigo} {cid}"],
                    "debilidades": [f"{marca}Debilidad IA {codigo} {cid}"],
                    "recomendacion": f"{marca}Recomendación IA {codigo} {cid}",
                }
                for cid, nivel in niveles.items()
            ],
            "aspectos_a_fortalecer": [f"{marca}Aspecto general {codigo}"],
            "retroalimentacion_general": "Bien",
        },
    )
    s.add(evaluacion)
    s.flush()
    for cid, nivel in niveles.items():
        s.add(
            EvaluacionCriterio(
                evaluacion_id=evaluacion.id,
                criterio_id=cid,
                nivel_ia=nivel,
                nivel_final=nivel,
                puntaje_normalizado=resultado.normalizados[cid],
                justificacion="Justificación",
                evidencias_verificadas=[
                    {
                        "fragmento": f"{marca}Cita {codigo} {cid}",
                        "fuente": "informe",
                        "ubicacion": "p. 1",
                        "verificada": True,
                        "similitud": 95.0,
                    },
                    {
                        "fragmento": f"NOVERIF {codigo} {cid}",
                        "fuente": "informe",
                        "ubicacion": None,
                        "verificada": False,
                        "similitud": 20.0,
                    },
                ],
            )
        )
    s.flush()
    return evaluacion.id


@pytest.fixture
def escenario(fabrica_api) -> dict[str, int]:
    """Estudiantes, temáticas, laboratorios con rúbrica y evaluaciones de todos los estados."""
    ids: dict[str, int] = {}
    with fabrica_api() as s:
        s.add_all(
            [
                Perfil(id=ID_EST, nombre=NOMBRE_MARCA, correo=CORREO_MARCA, rol="estudiante"),
                Perfil(id=ID_BETO, nombre="beto Ramírez", correo="b@x.co", rol="estudiante"),
                Perfil(id=ID_SIN_NOMBRE, nombre=None, rol="estudiante"),
            ]
        )
        for tid, nombre, padre in [*TEMATICAS, SUBTEMA]:
            s.add(Tematica(id=tid, nombre=nombre, padre_id=padre))
            s.flush()
        for codigo, (lab_id, cohorte) in LABS.items():
            s.add(Laboratorio(id=lab_id, cohorte_id=cohorte, codigo=codigo, titulo=f"Lab {codigo}"))
            s.flush()
            s.add(Rubrica(id=lab_id, laboratorio_id=lab_id))
            s.flush()
            s.add(
                RubricaVersion(
                    id=lab_id,
                    rubrica_id=lab_id,
                    version=1,
                    contenido=copy.deepcopy(RUBRICA),
                    estado="aprobada",
                )
            )
        s.flush()
        # C2-02: la publicada más reciente (4,4) se crea ANTES que una publicada antigua (0,0).
        ids["c2_02"] = _evaluacion(
            s, ID_EST, "C2-02", {"C1": "Bueno", "C2": "Alto"}, publicada_en=T0 + timedelta(days=5)
        )
        ids["c2_02_vieja"] = _evaluacion(
            s,
            ID_EST,
            "C2-02",
            {"C1": "Insuficiente", "C2": "Bajo"},
            publicada_en=T0 + timedelta(days=1),
            marca="OCULTA ",
        )
        ids["c1_01"] = _evaluacion(
            s, ID_EST, "C1-01", {"C1": "Bueno", "C2": "Medio"}, publicada_en=T0 + timedelta(days=2)
        )
        ids["c1_02"] = _evaluacion(
            s, ID_EST, "C1-02", {"C1": "Regular", "C2": "Alto"}, publicada_en=T0 + timedelta(days=3)
        )
        ids["c2_01"] = _evaluacion(
            s,
            ID_EST,
            "C2-01",
            {"C1": "Excelente", "C2": "Alto"},
            publicada_en=T0 + timedelta(days=4),
        )
        for estado in ("procesando", "borrador", "en_revision", "aprobada", "error"):
            _evaluacion(
                s, ID_EST, "C1-01", {"C1": "Excelente", "C2": "Alto"}, estado, marca="OCULTA "
            )
        ids["c1_03"] = _evaluacion(
            s, ID_EST, "C1-03", {"C1": "Insuficiente", "C2": "Bajo"}, "aprobada", marca="OCULTA "
        )
        # Beto: dos publicadas del MISMO laboratorio (cuenta 1) y un borrador en otro.
        _evaluacion(s, ID_BETO, "C1-01", {"C1": "Excelente", "C2": "Alto"}, publicada_en=T0)
        _evaluacion(s, ID_BETO, "C1-01", {"C1": "Bueno", "C2": "Alto"}, publicada_en=T0)
        _evaluacion(s, ID_BETO, "C1-02", {"C1": "Bueno", "C2": "Alto"}, "borrador")
        # La docente editó la debilidad y la recomendación de C1 en C1-01 (publicada).
        fila = s.scalar(
            select(EvaluacionCriterio).where(
                EvaluacionCriterio.evaluacion_id == ids["c1_01"],
                EvaluacionCriterio.criterio_id == "C1",
            )
        )
        fila.retroalimentacion_docente = {
            "debilidades": ["Debilidad editada por la docente"],
            "recomendacion": "Recomendación editada por la docente",
        }
        s.commit()
    return ids


class IAFalsa:
    """IA inyectable: registra lo que recibe y devuelve textos con números inventados."""

    def __init__(self) -> None:
        self.datos_recibidos: list[dict] = []
        self.mapeos: list[dict] = []
        self.tematicas_recibidas: list[list[str]] = []
        self.error_narrativa: Exception | None = None
        self.error_mapeo: Exception | None = None
        self.versiones: dict[str, str | None] = {"informe": "inf-1", "mapeo": "map-1"}

    def version_prompt(self, tarea: str) -> str | None:
        return self.versiones[tarea]

    def narrativa(self, datos: dict, config) -> NarrativaIA:
        self.datos_recibidos.append(copy.deepcopy(datos))
        if self.error_narrativa is not None:
            raise self.error_narrativa
        return NarrativaIA(
            competencias_desarrolladas=["Programación con promedio 9.9"],
            brechas=["Comunicación con 0.1"],
            plan_fortalecimiento=[
                AccionPlanIA(
                    accion="Practicar",
                    recurso="Curso X",
                    prioridad="alta",
                    competencia="Programación",
                )
            ],
            conclusion="Tu promedio general es 7.7",
            version_prompt=self.versiones["informe"],
            proveedor="falso",
            modelo="falso-1",
            respuestas_crudas=['{"crudo": "CRUDO_INFORME_QX", "promedio_general": 9.9}'],
        )

    def mapear(self, rubrica: dict, tematicas: list[str], config) -> MapeoIA:
        self.mapeos.append(copy.deepcopy(rubrica))
        self.tematicas_recibidas.append(list(tematicas))
        if self.error_mapeo is not None:
            raise self.error_mapeo
        return MapeoIA(
            criterios=[
                MapeoCriterioIA("C1", ["Redes neuronales"], ["Perceptrón"]),
                MapeoCriterioIA(
                    "C2",
                    ["Ética y verificación", "No existe"],
                    ["Comunicación de resultados", "Citas"],
                ),
            ],
            version_prompt=self.versiones["mapeo"],
            proveedor="falso",
            modelo="falso-1",
            respuestas_crudas=['{"crudo": "CRUDO_MAPEO_QX"}'],
        )


@pytest.fixture
def ia() -> IAFalsa:
    return IAFalsa()


@pytest.fixture
def cli(cliente_api, escenario, ia):
    cliente_api.app.dependency_overrides[obtener_ia_informe] = lambda: ia
    return cliente_api


def get(cliente, ruta: str, usuario: uuid.UUID | None = ID_DOCENTE, **params):
    headers = auth(usuario) if usuario else {}
    return cliente.get(ruta, headers=headers, params=params)


def informe(cliente, estudiante=ID_EST, usuario=ID_DOCENTE):
    return get(cliente, f"/api/estudiantes/{estudiante}/informe", usuario)


def mapa(cliente, estudiante=ID_EST, usuario=ID_DOCENTE):
    return get(cliente, f"/api/estudiantes/{estudiante}/mapa", usuario)


def error(respuesta, codigo: int) -> str:
    """Comprueba el código y la forma {"detail": "<texto>"}."""
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"detail"}
    assert isinstance(cuerpo["detail"], str) and cuerpo["detail"]
    return cuerpo["detail"]


def auditorias(fabrica, accion: str) -> list[Auditoria]:
    with fabrica() as s:
        filas = list(s.scalars(select(Auditoria).where(Auditoria.accion == accion)))
        s.expunge_all()
        return filas


def publicar(fabrica, evaluacion_id: int, cuando: datetime) -> None:
    with fabrica() as s:
        evaluacion = s.get(Evaluacion, evaluacion_id)
        evaluacion.estado = "publicada"
        evaluacion.publicada_en = cuando
        s.commit()


# ---------- Permisos ----------


@pytest.mark.parametrize("ruta", ROUTES)
def test_sin_token_401(cli, ruta):
    error(get(cli, ruta.format(id=ID_EST), usuario=None), 401)


def test_estudiante_no_lista_estudiantes_403(cli):
    error(get(cli, "/api/estudiantes", ID_EST), 403)


@pytest.mark.parametrize("ruta", ROUTES[1:])
def test_estudiante_pide_otro_estudiante_404(cli, ia, ruta):
    error(get(cli, ruta.format(id=ID_BETO), ID_EST), 404)
    assert ia.datos_recibidos == [] and ia.mapeos == []


@pytest.mark.parametrize("ruta", ROUTES[1:])
@pytest.mark.parametrize("objetivo", [ID_DOCENTE, ID_ADMIN, uuid.UUID(int=12345)])
def test_id_inexistente_o_no_estudiante_404(cli, ruta, objetivo):
    error(get(cli, ruta.format(id=objetivo), ID_DOCENTE), 404)


@pytest.mark.parametrize("ruta", ROUTES[1:])
def test_id_no_uuid_422(cli, ruta):
    error(get(cli, ruta.format(id="abc"), ID_DOCENTE), 422)


@pytest.mark.parametrize("ruta", ROUTES)
@pytest.mark.parametrize("usuario", [ID_DOCENTE, ID_ADMIN])
def test_docente_y_admin_ok(cli, ruta, usuario):
    assert get(cli, ruta.format(id=ID_EST), usuario).status_code == 200


@pytest.mark.parametrize("ruta", ROUTES[1:])
def test_estudiante_ve_lo_propio(cli, ruta):
    assert get(cli, ruta.format(id=ID_EST), ID_EST).status_code == 200


# ---------- Listado de estudiantes ----------


def test_listado_estudiantes(cli):
    r = get(cli, "/api/estudiantes")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 4 and cuerpo["limit"] == 20 and cuerpo["offset"] == 0
    items = cuerpo["items"]
    # Orden por nombre sin distinguir mayúsculas; sin nombre al final; sin docentes ni admin.
    assert [i["nombre"] for i in items] == ["Ana Estudiante", "beto Ramírez", NOMBRE_MARCA, None]
    assert all(set(i) == {"id", "nombre", "correo", "laboratorios_evaluados"} for i in items)
    por_id = {i["id"]: i["laboratorios_evaluados"] for i in items}
    # ID_EST: 4 laboratorios distintos con publicada (C1-03 solo aprobada no cuenta).
    # Beto: 2 publicadas del mismo laboratorio → 1; el borrador no cuenta.
    assert por_id == {str(ID_ESTUDIANTE): 0, str(ID_BETO): 1, str(ID_EST): 4, str(ID_SIN_NOMBRE): 0}
    assert items[2]["correo"] == CORREO_MARCA


def test_listado_paginacion(cli):
    r = get(cli, "/api/estudiantes", limit=2, offset=1)
    cuerpo = r.json()
    assert [i["nombre"] for i in cuerpo["items"]] == ["beto Ramírez", NOMBRE_MARCA]
    assert (cuerpo["total"], cuerpo["limit"], cuerpo["offset"]) == (4, 2, 1)
    assert get(cli, "/api/estudiantes", offset=10).json()["items"] == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_listado_paginacion_invalida_422(cli, params):
    error(get(cli, "/api/estudiantes", **params), 422)


# ---------- Informe: números ----------


def test_informe_numeros_y_orden(cli):
    r = informe(cli)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    labs = cuerpo["laboratorios"]
    # Orden cronológico: cohorte y luego código (aunque los ids estén en otro orden).
    assert [lab["codigo"] for lab in labs] == ["C1-01", "C1-02", "C2-01", "C2-02"]
    # Solo publicadas: C1-01 tiene un borrador/aprobada con 5,0 que no cuenta; en C2-02 cuenta la
    # publicada más reciente (4,4) y no la antigua (0,0); C1-03 (solo aprobada) no aparece.
    assert [lab["nota"] for lab in labs] == [3.5, 3.8, 5.0, 4.4]
    assert [lab["cohorte_numero"] for lab in labs] == [1, 1, 2, 2]
    assert cuerpo["laboratorios_evaluados"] == 4
    # Cohorte 1 = (3,5 + 3,8) / 2 = 3,65 exacto → ROUND_HALF_UP → 3,7.
    # Con float daría 3,6 (3,65 en binario es 3,6499999...) y con redondeo bancario también 3,6.
    assert round((3.5 + 3.8) / 2, 1) == 3.6
    promedios = {p["cohorte_numero"]: p["promedio"] for p in cuerpo["promedios_cohorte"]}
    assert promedios == {1: 3.7, 2: 4.7}  # cohorte 2 = (5,0 + 4,4) / 2 = 4,7
    # General = promedio de las notas de los 4 laboratorios = 16,7 / 4 = 4,175 → 4,2.
    assert cuerpo["promedio_general"] == 4.2
    # Evolución = promedio cohorte 2 − promedio cohorte 1 (ya redondeados) = 4,7 − 3,7 = 1,0.
    assert cuerpo["evolucion"] == {
        "cohorte_inicial": "Cohorte 1",
        "cohorte_final": "Cohorte 2",
        "promedio_inicial": 3.7,
        "promedio_final": 4.7,
        "diferencia": 1.0,
    }


def test_informe_dominio_por_competencia_y_tematica(cli):
    cuerpo = informe(cli).json()
    # Programación (C1): normalizados 0,75; 0,5; 1; 0,75 → ×5 = 3,75; 2,5; 5; 3,75 → 15/4 = 3,75
    # → 3,8. Comunicación (C2): 2/3; 1; 1; 1 → ×5 = 3,33; 5; 5; 5 → 18,33/4 = 4,58 → 4,6.
    assert cuerpo["competencias"] == [
        {"competencia": "Comunicación", "promedio": 4.6, "nivel_dominio": "alto",
         "criterios_evaluados": 4},
        {"competencia": "Programación", "promedio": 3.8, "nivel_dominio": "medio",
         "criterios_evaluados": 4},
    ]
    # Temáticas (mapeo falso): C1 → Redes neuronales (subtema de Aprendizaje automático),
    # C2 → Ética y verificación. El padre agrega lo de sus subtemas. "No existe" se ignora.
    assert cuerpo["tematicas"] == [
        {"tematica_id": 1, "tematica": "Aprendizaje automático", "promedio": 3.8,
         "nivel_dominio": "medio", "criterios_evaluados": 4},
        {"tematica_id": 2, "tematica": "Ética y verificación", "promedio": 4.6,
         "nivel_dominio": "alto", "criterios_evaluados": 4},
        {"tematica_id": 3, "tematica": "Redes neuronales", "promedio": 3.8,
         "nivel_dominio": "medio", "criterios_evaluados": 4},
    ]
    assert cuerpo["avisos"] == []


@pytest.mark.parametrize(
    ("valor", "nivel"), [(None, None), (0.0, "bajo"), (2.9, "bajo"), (3.0, "medio"),
                         (3.9, "medio"), (4.0, "alto"), (5.0, "alto")]
)
def test_umbrales_nivel_dominio(valor, nivel):
    from decimal import Decimal

    assert nivel_dominio(None if valor is None else Decimal(str(valor))) == nivel


def test_informe_igual_para_estudiante_y_docente(cli):
    docente = informe(cli).json()
    estudiante = informe(cli, usuario=ID_EST).json()
    assert estudiante == docente


# ---------- Informe: IA ----------


def test_datos_desempeno_sin_datos_personales(cli, ia):
    assert informe(cli).status_code == 200
    (datos,) = ia.datos_recibidos
    texto = json.dumps(datos, ensure_ascii=False)
    for marca in (NOMBRE_MARCA, "MARCANOMBREQX", CORREO_MARCA, "ejemplo.edu", str(ID_EST),
                  ID_EST.hex, "7e57a1b2", str(ID_DOCENTE)):
        assert marca not in texto
    for clave in ("evaluacion_id", "entrega_id", "estudiante", "correo", "nombre", "id"):
        assert f'"{clave}"' not in texto
    # Forma exacta de DatosDesempeno (Rol 1, extra="forbid").
    assert set(datos) == {
        "laboratorios", "promedios_cohorte", "promedio_general", "tematicas", "competencias",
        "evolucion",
    }
    assert all(set(x) == {"laboratorio", "cohorte", "nota"} for x in datos["laboratorios"])
    assert all(set(x) == {"cohorte", "promedio"} for x in datos["promedios_cohorte"])
    assert all(set(x) == {"tematica", "promedio", "nivel_dominio"} for x in datos["tematicas"])
    assert all(
        set(x) == {"competencia", "promedio", "nivel_dominio"} for x in datos["competencias"]
    )
    assert all(
        set(x) == {"cohorte_inicial", "cohorte_final", "promedio_inicial", "promedio_final",
                   "diferencia"}
        for x in datos["evolucion"]
    )
    assert [x["nota"] for x in datos["laboratorios"]] == [3.5, 3.8, 5.0, 4.4]
    assert datos["promedio_general"] == 4.2
    assert datos["evolucion"][0]["diferencia"] == 1.0


def test_la_ia_no_produce_ni_modifica_numeros(cli, ia):
    cuerpo = informe(cli).json()
    narrativa = cuerpo["narrativa"]
    assert narrativa["estado"] == "generada"
    assert narrativa["competencias_desarrolladas"] == ["Programación con promedio 9.9"]
    assert narrativa["plan_fortalecimiento"][0]["prioridad"] == "alta"
    assert narrativa["conclusion"] == "Tu promedio general es 7.7"
    numeros = json.dumps({k: v for k, v in cuerpo.items() if k != "narrativa"})
    for raro in ("9.9", "7.7", "0.1"):
        assert raro not in numeros
    assert cuerpo["promedio_general"] == 4.2
    assert "CRUDO_INFORME_QX" not in json.dumps(cuerpo)
    assert set(narrativa) == {
        "estado", "mensaje", "competencias_desarrolladas", "brechas", "plan_fortalecimiento",
        "conclusion", "generada_en",
    }


def test_traductores_ignoran_numeros_y_campos_extra():
    accion = SimpleNamespace(accion="A", recurso="R", prioridad="media", competencia="P", nota=9.9)
    crudo = SimpleNamespace(
        informe=SimpleNamespace(
            competencias_desarrolladas=["x"], brechas=["y"], plan_fortalecimiento=[accion],
            conclusion="z", promedio_general=9.9, nota=9.9,
        ),
        version_prompt="1.0", proveedor="p", modelo="m", respuestas_crudas=["c"], nota=9.9,
        temperatura=0.1,
    )
    narrativa = traducir_narrativa(crudo)
    assert narrativa.plan_fortalecimiento == [AccionPlanIA("A", "R", "media", "P")]
    assert not any(isinstance(getattr(narrativa, c), float) for c in vars(narrativa))
    mapeo = traducir_mapeo(
        SimpleNamespace(
            mapeo=SimpleNamespace(
                mapeos=[SimpleNamespace(criterio_id="C1", tematicas=["T"], conceptos=["k"])]
            ),
            version_prompt="1.0", proveedor="p", modelo="m", respuestas_crudas=["c"],
        )
    )
    assert mapeo.criterios == [MapeoCriterioIA("C1", ["T"], ["k"])]


def test_sin_evaluaciones_publicadas_no_llama_a_la_ia(cli, ia):
    cuerpo = informe(cli, estudiante=ID_ESTUDIANTE).json()
    assert cuerpo["laboratorios"] == [] and cuerpo["laboratorios_evaluados"] == 0
    assert cuerpo["promedio_general"] is None
    assert [p["promedio"] for p in cuerpo["promedios_cohorte"]] == [None, None]
    assert cuerpo["competencias"] == [] and cuerpo["tematicas"] == []
    assert cuerpo["evolucion"]["diferencia"] is None
    assert cuerpo["narrativa"]["estado"] == "sin_datos"
    assert cuerpo["narrativa"]["mensaje"]
    assert ia.datos_recibidos == [] and ia.mapeos == []


def test_narrativa_no_disponible_sin_modulos_de_ia(cli, monkeypatch, fabrica_api):
    # Simula que app.ia.informe y app.ia.tematicas no existen: el import lanza ImportError.
    monkeypatch.setitem(sys.modules, "app.ia.informe", None)
    monkeypatch.setitem(sys.modules, "app.ia.tematicas", None)
    cli.app.dependency_overrides[obtener_ia_informe] = lambda: IAInformeReal()
    cuerpo = informe(cli).json()
    assert cuerpo["promedio_general"] == 4.2
    assert [lab["nota"] for lab in cuerpo["laboratorios"]] == [3.5, 3.8, 5.0, 4.4]
    assert cuerpo["narrativa"]["estado"] == "no_disponible"
    assert cuerpo["narrativa"]["mensaje"]
    assert cuerpo["narrativa"]["competencias_desarrolladas"] == []
    assert cuerpo["tematicas"] == [] and cuerpo["avisos"]
    assert len(cuerpo["competencias"]) == 2
    # El mapa funciona agrupando por competencia.
    grafo = mapa(cli).json()
    tipos = {n["id"]: n["tipo"] for n in grafo["nodos"]}
    assert tipos["competencia:programacion"] == "competencia"
    assert grafo["avisos"]
    assert auditorias(fabrica_api, "generar_informe_ia") == []


@pytest.mark.parametrize(
    "excepcion",
    [
        RuntimeError("MARCADOR_FALLO_QX"),
        GeneracionIAError("MARCADOR_FALLO_QX", errores=["e"], respuestas_crudas=["CRUDO_ERR_QX"]),
    ],
)
def test_error_de_la_ia_mensaje_generico_y_detalle_en_auditoria(cli, ia, fabrica_api, excepcion):
    ia.error_narrativa = excepcion
    r = informe(cli)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["narrativa"]["estado"] == "error"
    assert cuerpo["narrativa"]["mensaje"]
    assert "MARCADOR_FALLO_QX" not in r.text and "CRUDO_ERR_QX" not in r.text
    assert cuerpo["promedio_general"] == 4.2
    (registro,) = auditorias(fabrica_api, "generar_informe_ia_error")
    assert registro.usuario_id == ID_DOCENTE
    assert registro.entidad == "perfiles" and registro.entidad_id == str(ID_EST)
    assert "MARCADOR_FALLO_QX" in json.dumps(registro.despues)


def test_generacion_queda_en_auditoria(cli, fabrica_api):
    r = informe(cli, usuario=ID_EST)
    assert "CRUDO_INFORME_QX" not in r.text and "CRUDO_MAPEO_QX" not in r.text
    (registro,) = auditorias(fabrica_api, "generar_informe_ia")
    assert registro.usuario_id == ID_EST
    assert (registro.entidad, registro.entidad_id) == ("perfiles", str(ID_EST))
    assert "CRUDO_INFORME_QX" in json.dumps(registro.despues)
    mapeos = auditorias(fabrica_api, "mapear_tematicas_ia")
    assert sorted(int(m.entidad_id) for m in mapeos) == [21, 22, 23, 24]
    assert all(m.entidad == "rubrica_versiones" for m in mapeos)
    assert "CRUDO_MAPEO_QX" in json.dumps(mapeos[0].despues)


# ---------- Caché: no llamar a la IA en cada GET ----------


def test_cache_reutiliza_y_regenera_si_cambian_los_datos(cli, ia, escenario, fabrica_api):
    primero = informe(cli).json()
    assert len(ia.datos_recibidos) == 1
    assert len(ia.mapeos) == 4  # una vez por versión de rúbrica (21, 22, 23, 24)
    # Nombres de la taxonomía enviados a la IA (todas las temáticas, incluidos subtemas).
    assert sorted(ia.tematicas_recibidas[0]) == sorted(
        ["Aprendizaje automático", "Ética y verificación", "Redes neuronales"]
    )
    segundo = informe(cli, usuario=ID_EST).json()
    assert segundo["narrativa"] == primero["narrativa"]
    mapa(cli)
    assert len(ia.datos_recibidos) == 1 and len(ia.mapeos) == 4
    # Se publica una evaluación nueva (C1-03): cambian los números → se regenera la narrativa y
    # solo se mapea la versión de rúbrica nueva.
    publicar(fabrica_api, escenario["c1_03"], T0 + timedelta(days=9))
    tercero = informe(cli).json()
    assert tercero["laboratorios_evaluados"] == 5
    assert len(ia.datos_recibidos) == 2 and len(ia.mapeos) == 5
    # Cambia la versión del prompt del informe → se regenera aunque los números sean iguales.
    ia.versiones["informe"] = "inf-2"
    informe(cli)
    assert len(ia.datos_recibidos) == 3
    assert len(auditorias(fabrica_api, "generar_informe_ia")) == 3


def test_error_no_se_cachea(cli, ia):
    ia.error_narrativa = RuntimeError("falla")
    assert informe(cli).json()["narrativa"]["estado"] == "error"
    ia.error_narrativa = None
    assert informe(cli).json()["narrativa"]["estado"] == "generada"
    assert len(ia.datos_recibidos) == 2


# ---------- Mapa de conocimiento ----------


def _nodos(grafo) -> dict[str, dict]:
    return {n["id"]: n for n in grafo["nodos"]}


def test_mapa_con_datos(cli):
    r = mapa(cli)
    assert r.status_code == 200, r.text
    grafo = r.json()
    nodos = _nodos(grafo)
    labs = {"lab:C1-01", "lab:C1-02", "lab:C2-01", "lab:C2-02"}
    conceptos = {"concepto:3:perceptron", "concepto:2:comunicacion-de-resultados",
                 "concepto:2:citas"}
    assert set(nodos) == {"tematica:1", "tematica:2", "tematica:3"} | conceptos | labs
    assert len(grafo["nodos"]) == len(nodos)  # ids únicos
    assert nodos["tematica:1"]["tipo"] == "tematica"
    assert nodos["tematica:3"]["tipo"] == "subtema"
    assert nodos["concepto:3:perceptron"]["tipo"] == "concepto"
    assert nodos["lab:C1-01"]["tipo"] == "laboratorio"
    aristas = {(a["origen"], a["destino"]) for a in grafo["aristas"]}
    esperadas = {("tematica:1", "tematica:3"), ("tematica:3", "concepto:3:perceptron"),
                 ("tematica:2", "concepto:2:comunicacion-de-resultados"),
                 ("tematica:2", "concepto:2:citas")}
    esperadas |= {(c, lab) for c in conceptos for lab in labs}
    assert aristas == esperadas
    assert len(grafo["aristas"]) == len(aristas)
    # Niveles: subtema y padre 3,8 (medio); ética 4,6 (alto); laboratorio = su nota.
    assert (nodos["tematica:3"]["dominio"], nodos["tematica:3"]["nivel_dominio"]) == (3.8, "medio")
    assert nodos["tematica:1"]["dominio"] == 3.8
    assert (nodos["tematica:2"]["dominio"], nodos["tematica:2"]["nivel_dominio"]) == (4.6, "alto")
    assert nodos["concepto:2:citas"]["dominio"] == 4.6
    assert (nodos["lab:C1-01"]["dominio"], nodos["lab:C1-01"]["nivel_dominio"]) == (3.5, "medio")
    assert nodos["lab:C2-01"]["nivel_dominio"] == "alto"
    assert nodos["concepto:3:perceptron"]["laboratorios"] == ["C1-01", "C1-02", "C2-01", "C2-02"]


def test_mapa_evidencias_y_aspectos(cli):
    texto = mapa(cli, usuario=ID_EST).text
    assert "OCULTA" not in texto  # nada de evaluaciones no publicadas
    assert "NOVERIF" not in texto  # solo citas verificadas
    assert "similitud" not in texto and "nivel_ia" not in texto
    nodos = _nodos(json.loads(texto))
    perceptron = nodos["concepto:3:perceptron"]
    assert {e["fragmento"] for e in perceptron["evidencias"]} == {
        "Cita C1-01 C1", "Cita C1-02 C1", "Cita C2-01 C1", "Cita C2-02 C1"
    }
    assert all(
        set(e) == {"fragmento", "fuente", "ubicacion", "laboratorio", "criterio_id"}
        for e in perceptron["evidencias"]
    )
    aspectos = perceptron["aspectos_por_profundizar"]
    # Texto editado por la docente en C1-01 en lugar del original de la IA.
    assert "Debilidad editada por la docente" in aspectos
    assert "Recomendación editada por la docente" in aspectos
    assert "Debilidad IA C1-01 C1" not in aspectos
    assert "Recomendación IA C1-01 C1" not in aspectos
    assert "Debilidad IA C1-02 C1" in aspectos
    assert "Aspecto general C1-01" in nodos["lab:C1-01"]["aspectos_por_profundizar"]


def test_mapa_igual_para_estudiante_y_docente(cli):
    assert mapa(cli, usuario=ID_EST).json() == mapa(cli).json()


def test_mapa_vacio_sin_publicadas(cli, ia):
    grafo = mapa(cli, estudiante=ID_ESTUDIANTE).json()
    assert grafo["nodos"] == [] and grafo["aristas"] == []
    assert ia.mapeos == []


def test_mapa_error_de_mapeo_agrupa_por_competencia(cli, ia, fabrica_api):
    ia.error_mapeo = RuntimeError("MARCADOR_MAPEO_QX")
    r = mapa(cli)
    assert r.status_code == 200
    assert "MARCADOR_MAPEO_QX" not in r.text
    grafo = r.json()
    nodos = _nodos(grafo)
    assert nodos["competencia:programacion"]["tipo"] == "competencia"
    assert nodos["competencia:programacion"]["dominio"] == 3.8
    assert nodos["competencia:comunicacion"]["dominio"] == 4.6
    assert "concepto:competencia-programacion:codigo" in nodos
    aristas = {(a["origen"], a["destino"]) for a in grafo["aristas"]}
    assert ("competencia:programacion", "concepto:competencia-programacion:codigo") in aristas
    assert ("concepto:competencia-programacion:codigo", "lab:C1-01") in aristas
    assert grafo["avisos"]
    errores = auditorias(fabrica_api, "mapear_tematicas_ia_error")
    assert errores and "MARCADOR_MAPEO_QX" in json.dumps(errores[0].despues)
    assert errores[0].entidad == "rubrica_versiones"
