"""Pruebas del script de datos semilla (idempotencia y mensajes)."""

from sqlalchemy import func, select

import seed
import seed_datos
from app.config import Settings
from app.models import Cohorte, ConfigIA, Laboratorio, Tematica


def _conteos(sesion) -> tuple[int, int, int, int]:
    """Cuenta filas de las tablas sembradas."""
    return tuple(
        sesion.scalar(select(func.count()).select_from(modelo))
        for modelo in (Cohorte, Laboratorio, Tematica, ConfigIA)
    )


def test_sembrar_inserta_datos_base(sesion):
    seed.sembrar(sesion)
    assert _conteos(sesion) == (
        2,
        len(seed_datos.LABORATORIOS),
        len(seed_datos.TEMATICAS),
        1,
    )
    numeros = set(sesion.scalars(select(Cohorte.numero)))
    assert numeros == {1, 2}
    config = sesion.get(ConfigIA, 1)
    assert config is not None and config.temperatura <= 0.2


def test_sembrar_es_idempotente(sesion):
    seed.sembrar(sesion)
    primera = _conteos(sesion)
    seed.sembrar(sesion)
    assert _conteos(sesion) == primera


def test_sembrar_no_sobrescribe_laboratorio_editado(sesion):
    seed.sembrar(sesion)
    lab = sesion.scalar(select(Laboratorio).where(Laboratorio.codigo == "C1-L1"))
    lab.titulo = "Título real editado por el docente"
    sesion.commit()
    seed.sembrar(sesion)
    sesion.refresh(lab)
    assert lab.titulo == "Título real editado por el docente"


def test_main_sin_database_url_termina_con_mensaje(monkeypatch, capsys):
    monkeypatch.setattr(seed, "get_settings", lambda: Settings(_env_file=None, database_url=""))
    assert seed.main() == 1
    assert "falta DATABASE_URL" in capsys.readouterr().out

