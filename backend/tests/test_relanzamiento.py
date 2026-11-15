"""Pruebas de la recuperación de evaluaciones atascadas (A1), la regla de relanzamiento del
estudiante (M2) y la verificación de código en el detalle docente (M7).

Sin IA real ni red: se usan el evaluador y el material falsos de tests/test_evaluaciones.py.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import Auditoria, Evaluacion, VerificacionCodigo
from app.services import evaluaciones as servicio
from tests.test_auth import ID_ADMIN, ID_DOCENTE, ID_ESTUDIANTE
from tests.test_evaluaciones import (
    MATERIAL,
    auditorias,
    auth,
    contar_evaluaciones,
    criterios_de,
    evaluar,
    leer,
    resultado_ia,
)

MSG_EN_CURSO = "Ya hay una evaluación en curso para esta entrega."
MSG_GENERICO = (
    "No se pudo completar la evaluación automática. Intenta de nuevo o contacta al docente."
)


def crear_evaluacion(fabrica, estado: str, minutos: int = 0, **extra) -> int:
    """Evaluación de la entrega 1 creada hace `minutos` minutos (0 = ahora, por el servidor)."""
    with fabrica() as s:
        evaluacion = Evaluacion(entrega_id=1, estado=estado, **extra)
        if minutos:
            evaluacion.creada_en = datetime.now(UTC) - timedelta(minutes=minutos)
        s.add(evaluacion)
        s.commit()
        return evaluacion.id


# ---------- A1: evaluaciones atascadas en `procesando` ----------


def test_procesando_reciente_sigue_bloqueando_409(cliente, datos, evaluador):
    viejo = crear_evaluacion(datos, "procesando", minutos=5)
    respuesta = evaluar(cliente, 1, ID_DOCENTE)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": MSG_EN_CURSO}
    assert leer(datos, viejo).estado == "procesando"
    assert contar_evaluaciones(datos) == 1
    assert evaluador.solicitudes == []


@pytest.mark.parametrize("usuario", [ID_ESTUDIANTE, ID_DOCENTE])
def test_procesando_atascada_pasa_a_error_y_relanzar_202(cliente, datos, usuario):
    viejo = crear_evaluacion(datos, "procesando", minutos=11, nota=Decimal("3.0"))
    respuesta = evaluar(cliente, 1, usuario)
    assert respuesta.status_code == 202, respuesta.text
    nuevo = respuesta.json()["evaluacion_id"]
    assert nuevo != viejo
    atascada = leer(datos, viejo)
    assert atascada.estado == "error"
    assert atascada.error == MSG_GENERICO
    assert atascada.nota is None
    assert leer(datos, nuevo).estado == "borrador"


def test_auditoria_de_la_recuperacion_sin_usuario(cliente, datos):
    viejo = crear_evaluacion(datos, "procesando", minutos=30)
    assert evaluar(cliente, 1, ID_DOCENTE).status_code == 202
    (fila,) = [a for a in auditorias(datos, viejo) if a.accion == "evaluacion_ia_error"]
    assert fila.usuario_id is None
    assert fila.despues == {"tipo": "TiempoAgotado", "minutos": 10}


def test_recuperacion_y_su_auditoria_en_la_misma_transaccion(cliente, datos):
    """Si falla la escritura de la auditoría, la evaluación NO pasa a error (todo o nada)."""
    viejo = crear_evaluacion(datos, "procesando", minutos=30)

    def _falla(session, _contexto, _instancias):
        if any(
            isinstance(o, Auditoria) and o.accion == "evaluacion_ia_error" for o in session.new
        ):
            raise OperationalError("INSERT INTO auditoria", {}, Exception("disco lleno"))

    event.listen(Session, "before_flush", _falla)
    try:
        respuesta = evaluar(cliente, 1, ID_DOCENTE)
    finally:
        event.remove(Session, "before_flush", _falla)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": MSG_EN_CURSO}
    assert leer(datos, viejo).estado == "procesando"
    assert auditorias(datos, viejo) == []
    assert contar_evaluaciones(datos) == 1


@pytest.mark.parametrize(
    "creada_en",
    [
        datetime(2026, 11, 14, 10, 0),  # SQLite: sin zona (se trata como UTC)
        datetime(2026, 11, 14, 10, 0, tzinfo=UTC),  # Postgres: con zona
        datetime(2026, 11, 14, 5, 0, tzinfo=UTC) + timedelta(hours=5),
    ],
    ids=["naive", "aware_utc", "aware_calculada"],
)
def test_esta_atascada_con_fechas_con_y_sin_zona(creada_en):
    ahora = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)
    assert servicio.MINUTOS_MAX_PROCESANDO == 10
    assert not servicio.esta_atascada(creada_en, ahora + timedelta(minutes=9))
    assert servicio.esta_atascada(creada_en, ahora + timedelta(minutes=11))


class EvaluadorTardio:
    """Evaluador que, mientras «piensa», ve cómo la recuperación marca la evaluación en error."""

    def __init__(self, fabrica, evaluacion_id: int, falla: bool = False) -> None:
        self.fabrica = fabrica
        self.evaluacion_id = evaluacion_id
        self.falla = falla

    def __call__(self, _solicitud):
        with self.fabrica() as s:
            evaluacion = s.get(Evaluacion, self.evaluacion_id)
            evaluacion.estado = "error"
            evaluacion.error = MSG_GENERICO
            s.commit()
        if self.falla:
            raise RuntimeError("la IA terminó tarde con error")
        return resultado_ia()


@pytest.mark.parametrize("falla", [False, True], ids=["exito_tardio", "error_tardio"])
def test_tarea_tardia_no_pisa_el_error(datos, falla):
    evaluacion_id = crear_evaluacion(datos, "procesando", minutos=11)
    servicio.ejecutar_evaluacion(
        evaluacion_id,
        ID_DOCENTE,
        datos,
        EvaluadorTardio(datos, evaluacion_id, falla),
        lambda _db, _entrega: MATERIAL,
    )
    ev = leer(datos, evaluacion_id)
    assert ev.estado == "error"
    assert ev.error == MSG_GENERICO
    assert ev.nota is None
    assert ev.resultado is None
    assert criterios_de(datos, evaluacion_id) == []
    acciones = [a.accion for a in auditorias(datos, evaluacion_id)]
    assert "evaluacion_ia" not in acciones
    assert "evaluacion_ia_error" not in acciones
    assert acciones.count("evaluacion_ia_descartada") == 1


# ---------- M2: el estudiante no relanza si hay una evaluación activa o publicada ----------


@pytest.mark.parametrize("estado", ["borrador", "en_revision", "aprobada", "publicada"])
def test_estudiante_con_evaluacion_activa_o_publicada_409(cliente, datos, evaluador, estado):
    crear_evaluacion(datos, estado)
    respuesta = evaluar(cliente, 1, ID_ESTUDIANTE)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detail": f"Esta entrega ya tiene una evaluación en estado '{estado}'; "
        "no puedes lanzar otra."
    }
    assert contar_evaluaciones(datos) == 1
    assert evaluador.solicitudes == []


def test_estudiante_con_procesando_reciente_409_en_curso(cliente, datos):
    crear_evaluacion(datos, "procesando")
    respuesta = evaluar(cliente, 1, ID_ESTUDIANTE)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": MSG_EN_CURSO}


def test_estudiante_con_solo_errores_202(cliente, datos):
    crear_evaluacion(datos, "error")
    crear_evaluacion(datos, "error")
    assert evaluar(cliente, 1, ID_ESTUDIANTE).status_code == 202


def test_estudiante_con_publicada_antigua_y_ultima_error_409(cliente, datos):
    crear_evaluacion(datos, "publicada", minutos=60)
    crear_evaluacion(datos, "error")
    respuesta = evaluar(cliente, 1, ID_ESTUDIANTE)
    assert respuesta.status_code == 409
    assert "'publicada'" in respuesta.json()["detail"]


@pytest.mark.parametrize("usuario", [ID_DOCENTE, ID_ADMIN])
def test_docente_y_admin_relanzan_con_publicada_202(cliente, datos, usuario):
    crear_evaluacion(datos, "publicada")
    assert evaluar(cliente, 1, usuario).status_code == 202


# ---------- M7: verificación de código en el detalle ----------

METRICAS = {
    "codigo_salida": 1,
    "tiene_error": True,
    "ejecucion_exitosa": False,
    "stderr": "Traceback SECRETO_STDERR",
}
RESUMEN = {"codigo_salida": 1, "tiene_error": True, "ejecucion_exitosa": False}


def con_verificacion(fabrica, estado: str) -> int:
    evaluacion_id = crear_evaluacion(fabrica, estado)
    with fabrica() as s:
        s.add(VerificacionCodigo(evaluacion_id=evaluacion_id, metricas=METRICAS))
        s.commit()
    return evaluacion_id


@pytest.mark.parametrize("usuario", [ID_DOCENTE, ID_ADMIN])
def test_detalle_docente_incluye_verificacion(cliente, datos, usuario):
    evaluacion_id = con_verificacion(datos, "borrador")
    respuesta = cliente.get(f"/api/evaluaciones/{evaluacion_id}", headers=auth(usuario))
    assert respuesta.status_code == 200
    assert respuesta.json()["verificacion"] == RESUMEN
    assert "SECRETO_STDERR" not in respuesta.text


def test_detalle_docente_sin_verificacion_null(cliente, datos):
    evaluacion_id = crear_evaluacion(datos, "borrador")
    respuesta = cliente.get(f"/api/evaluaciones/{evaluacion_id}", headers=auth(ID_DOCENTE))
    assert respuesta.json()["verificacion"] is None


def test_detalle_estudiante_no_ve_verificacion(cliente, datos):
    evaluacion_id = con_verificacion(datos, "publicada")
    respuesta = cliente.get(f"/api/evaluaciones/{evaluacion_id}", headers=auth(ID_ESTUDIANTE))
    assert respuesta.status_code == 200
    assert respuesta.json()["verificacion"] is None
    assert "SECRETO_STDERR" not in respuesta.text
