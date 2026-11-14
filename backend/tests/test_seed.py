"""Pruebas del script de datos semilla (laboratorios de demo, rúbricas, idempotencia)."""

import json

import pytest
from sqlalchemy import func, select

import seed
import seed_datos
from app.config import Settings
from app.models import Cohorte, ConfigIA, Laboratorio, Rubrica, RubricaVersion, Tematica
from app.services.nota import calcular_nota
from app.services.rubricas import validar_rubrica

ESPERADOS = {
    "C1-01": (1, "rubrica_fundamentos_ia.json"),
    "C1-02": (1, "rubrica_manizales.json"),
    "C2-01": (2, "rubrica_lab01.json"),
    "C2-02": (2, "rubrica_lab03.json"),
}


def _leer_json(nombre: str) -> dict:
    """Lee una rúbrica de demo desde backend/rubricas_demo/."""
    return json.loads((seed.CARPETA_RUBRICAS / nombre).read_text(encoding="utf-8"))


def _conteos(sesion) -> tuple[int, ...]:
    """Cuenta filas de las tablas sembradas."""
    return tuple(
        sesion.scalar(select(func.count()).select_from(modelo))
        for modelo in (Cohorte, Laboratorio, Rubrica, RubricaVersion, Tematica, ConfigIA)
    )


def _versiones(sesion, codigo: str) -> list[RubricaVersion]:
    """Versiones de rúbrica del laboratorio con ese código."""
    return list(
        sesion.scalars(
            select(RubricaVersion)
            .join(Rubrica)
            .join(Laboratorio)
            .where(Laboratorio.codigo == codigo)
            .order_by(RubricaVersion.version)
        )
    )


@pytest.mark.parametrize("archivo", [a for _, a in ESPERADOS.values()])
def test_rubricas_demo_son_validas_y_calculan_nota(archivo):
    rubrica = _leer_json(archivo)
    assert validar_rubrica(rubrica) == []
    criterios = rubrica["criterios"]
    maximo = {c["id"]: max(c["niveles"], key=lambda n: n["puntaje"])["nombre"] for c in criterios}
    minimo = {c["id"]: min(c["niveles"], key=lambda n: n["puntaje"])["nombre"] for c in criterios}
    assert float(calcular_nota(criterios, maximo).nota) == 5.0
    assert float(calcular_nota(criterios, minimo).nota) == 0.0


def test_datos_semilla_apuntan_a_los_cuatro_laboratorios():
    assert {d["codigo"]: (d["cohorte"], d["rubrica_archivo"]) for d in seed_datos.LABORATORIOS} == (
        ESPERADOS
    )


def test_sembrar_crea_laboratorios_de_demo_con_rubrica(sesion):
    seed.sembrar(sesion)
    labs = sesion.scalars(select(Laboratorio)).all()
    assert len(labs) == 4
    for lab in labs:
        cohorte, archivo = ESPERADOS[lab.codigo]
        assert sesion.get(Cohorte, lab.cohorte_id).numero == cohorte
        assert "PROVISIONAL" not in lab.titulo
        assert lab.descripcion and lab.objetivos
        versiones = _versiones(sesion, lab.codigo)
        assert len(versiones) == 1
        assert versiones[0].version == 1
        assert versiones[0].estado == "aprobada"
        assert versiones[0].creada_por is None
        assert versiones[0].contenido == _leer_json(archivo)
    assert _conteos(sesion)[4:] == (len(seed_datos.TEMATICAS), 1)
    assert set(sesion.scalars(select(Cohorte.numero))) == {1, 2}
    assert sesion.get(ConfigIA, 1).temperatura <= 0.2


def test_sembrar_es_idempotente(sesion):
    seed.sembrar(sesion)
    primera = _conteos(sesion)
    seed.sembrar(sesion)
    assert _conteos(sesion) == primera
    assert primera[:4] == (2, 4, 4, 4)


def test_sembrar_no_sobrescribe_laboratorio_editado(sesion):
    seed.sembrar(sesion)
    lab = sesion.scalar(select(Laboratorio).where(Laboratorio.codigo == "C1-01"))
    lab.titulo = "Título editado por el docente"
    sesion.commit()
    seed.sembrar(sesion)
    sesion.refresh(lab)
    assert lab.titulo == "Título editado por el docente"


def test_sembrar_no_toca_rubrica_con_versiones_del_docente(sesion):
    seed.sembrar(sesion)
    v1 = _versiones(sesion, "C2-02")[0]
    contenido_docente = {**v1.contenido, "titulo": "Versión ajustada por el docente"}
    sesion.add(
        RubricaVersion(
            rubrica_id=v1.rubrica_id, version=2, estado="aprobada", contenido=contenido_docente
        )
    )
    sesion.commit()
    seed.sembrar(sesion)
    versiones = _versiones(sesion, "C2-02")
    assert [v.version for v in versiones] == [1, 2]
    assert versiones[1].contenido == contenido_docente


def test_sembrar_no_crea_version_si_el_laboratorio_ya_tiene_una(sesion):
    cohorte = Cohorte(numero=2, nombre="Cohorte 2")
    sesion.add(cohorte)
    sesion.flush()
    lab = Laboratorio(cohorte_id=cohorte.id, codigo="C2-01", titulo="Creado por el docente")
    sesion.add(lab)
    sesion.flush()
    rubrica = Rubrica(laboratorio_id=lab.id)
    sesion.add(rubrica)
    sesion.flush()
    propia = {"titulo": "Propia", "criterios": []}
    sesion.add(
        RubricaVersion(rubrica_id=rubrica.id, version=3, estado="aprobada", contenido=propia)
    )
    sesion.commit()
    seed.sembrar(sesion)
    versiones = _versiones(sesion, "C2-01")
    assert [(v.version, v.contenido) for v in versiones] == [(3, propia)]


def test_sembrar_aborta_si_una_rubrica_tiene_inconsistencias(sesion, monkeypatch, tmp_path):
    for _, archivo in ESPERADOS.values():
        (tmp_path / archivo).write_text(json.dumps(_leer_json(archivo)), encoding="utf-8")
    mala = _leer_json("rubrica_lab01.json")
    mala["criterios"][0]["ponderacion"] = 50
    (tmp_path / "rubrica_lab01.json").write_text(json.dumps(mala), encoding="utf-8")
    monkeypatch.setattr(seed, "CARPETA_RUBRICAS", tmp_path)
    with pytest.raises(seed.SemillaInvalidaError, match="rubrica_lab01.json tiene inconsistencias"):
        seed.sembrar(sesion)
    assert _conteos(sesion) == (0, 0, 0, 0, 0, 0)


def test_main_con_rubrica_invalida_muestra_mensaje_sin_traceback(monkeypatch, capsys, tmp_path):
    (tmp_path / "rubrica_fundamentos_ia.json").write_text("{no es json", encoding="utf-8")
    monkeypatch.setattr(seed, "CARPETA_RUBRICAS", tmp_path)
    monkeypatch.setattr(seed, "get_settings", lambda: Settings(_env_file=None, database_url="x"))

    class _SesionFalsa:
        def __enter__(self):
            return object()

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(seed, "SessionLocal", _SesionFalsa)
    assert seed.main() == 1
    salida = capsys.readouterr().out
    assert "no se cargó ningún dato" in salida
    assert "rubrica_fundamentos_ia.json" in salida
    assert "Traceback" not in salida


def test_main_sin_database_url_termina_con_mensaje(monkeypatch, capsys):
    monkeypatch.setattr(seed, "get_settings", lambda: Settings(_env_file=None, database_url=""))
    assert seed.main() == 1
    assert "falta DATABASE_URL" in capsys.readouterr().out
