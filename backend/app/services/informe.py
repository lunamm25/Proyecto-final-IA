"""Informe integrado del aprendizaje (RF-08): números del backend + narrativa de la IA.

Números (ver services/desempeno.py): nota por laboratorio (la de la evaluación publicada que
cuenta), promedio por cohorte y general (promedio simple de las notas de laboratorio), dominio por
competencia y por temática (promedio de normalizado × 5) y evolución (promedio de la última cohorte
− promedio de la primera, ambos ya redondeados; null si falta alguno).
La IA solo redacta con `DatosDesempeno` (sin nombre, correo ni ids). La narrativa se guarda en
`cache_ia` por huella de esos datos + versión del prompt: si nada cambió, no se vuelve a llamar.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import CacheIA, Cohorte, Perfil, Tematica
from app.services import cache_ia
from app.services.desempeno import (
    EvaluacionContada,
    dominio,
    estudiante_visible,
    evaluaciones_contadas,
    fraccion,
    muestra,
    nivel_dominio,
    numero,
    promedio,
)
from app.services.evaluaciones import configuracion_ia
from app.services.evaluador_ia import ConfigProveedor
from app.services.informe_ia import IAInforme, IANoDisponibleError, NarrativaIA, detalle_error
from app.services.mapeo_tematicas import (
    MapeoVersion,
    ancestros,
    cargar_taxonomia,
    obtener_mapeos,
    slug,
)

TIPO = "informe_narrativo"
LIMITE_NOMBRE = 200

MSG_SIN_DATOS = "Aún no hay evaluaciones publicadas; el informe se completará cuando las haya."
MSG_NO_DISPONIBLE = "La redacción del informe con IA no está disponible en esta versión."
MSG_ERROR = (
    "No se pudo generar la redacción del informe con IA. Los datos numéricos están completos; "
    "intenta de nuevo más tarde."
)
AVISO_SIN_MAPEO = (
    "Algunos criterios no se pudieron asociar con temáticas; el dominio por temática puede estar "
    "incompleto."
)
AVISO_SIN_TAXONOMIA = "No hay temáticas configuradas; no se calcula el dominio por temática."


@dataclass(frozen=True)
class LaboratorioInforme:
    """Nota de un laboratorio (la de su evaluación publicada que cuenta)."""

    contada: EvaluacionContada
    nota: Decimal | None


@dataclass(frozen=True)
class PromedioCohorte:
    """Promedio de las notas de una cohorte."""

    cohorte: Cohorte
    promedio: Decimal | None
    laboratorios_evaluados: int


@dataclass(frozen=True)
class DominioGrupo:
    """Dominio 0–5 y nivel de una competencia o temática."""

    nombre: str
    promedio: Decimal | None
    nivel: str | None
    criterios_evaluados: int
    tematica_id: int | None = None


@dataclass(frozen=True)
class Evolucion:
    """Cambio entre la primera y la última cohorte."""

    cohorte_inicial: str
    cohorte_final: str
    promedio_inicial: Decimal | None
    promedio_final: Decimal | None
    diferencia: Decimal | None


@dataclass(frozen=True)
class Narrativa:
    """Textos de la IA y su estado: generada, sin_datos, no_disponible o error."""

    estado: str
    mensaje: str | None = None
    competencias_desarrolladas: list[str] = field(default_factory=list)
    brechas: list[str] = field(default_factory=list)
    plan_fortalecimiento: list[dict[str, str]] = field(default_factory=list)
    conclusion: str | None = None
    generada_en: datetime | None = None


@dataclass(frozen=True)
class Informe:
    """Informe completo: números del backend y narrativa por separado."""

    estudiante: Perfil
    laboratorios: list[LaboratorioInforme]
    promedios_cohorte: list[PromedioCohorte]
    promedio_general: Decimal | None
    competencias: list[DominioGrupo]
    tematicas: list[DominioGrupo]
    evolucion: Evolucion | None
    narrativa: Narrativa
    avisos: list[str]


# ---------- Números ----------


def _promedios_cohorte(
    db: Session, laboratorios: list[LaboratorioInforme]
) -> list[PromedioCohorte]:
    """Promedio por cohorte (todas las cohortes, en orden; None si no tiene notas)."""
    notas: dict[int, list[Fraction]] = defaultdict(list)
    for lab in laboratorios:
        if lab.nota is not None:
            notas[lab.contada.cohorte.id].append(fraccion(lab.nota))
    cohortes = db.scalars(select(Cohorte).order_by(Cohorte.numero))
    return [PromedioCohorte(c, promedio(notas[c.id]), len(notas[c.id])) for c in cohortes]


def _evolucion(promedios: list[PromedioCohorte]) -> Evolucion | None:
    """Última cohorte − primera (promedios ya redondeados); None si hay menos de 2 cohortes."""
    if len(promedios) < 2:
        return None
    inicial, final = promedios[0], promedios[-1]
    diferencia = None
    if inicial.promedio is not None and final.promedio is not None:
        diferencia = final.promedio - inicial.promedio
    return Evolucion(
        inicial.cohorte.nombre, final.cohorte.nombre, inicial.promedio, final.promedio, diferencia
    )


def _grupo(nombre: str, muestras: list[Fraction], tematica_id: int | None = None) -> DominioGrupo:
    """Dominio y nivel de un grupo de muestras."""
    valor = dominio(muestras)
    return DominioGrupo(nombre, valor, nivel_dominio(valor), len(muestras), tematica_id)


def _competencias(contadas: list[EvaluacionContada]) -> list[DominioGrupo]:
    """Dominio por competencia (orden alfabético sin acentos)."""
    muestras: dict[str, list[Fraction]] = defaultdict(list)
    for contada in contadas:
        for criterio in contada.criterios:
            valor = muestra(criterio)
            if valor is not None:
                muestras[criterio.competencia].append(valor)
    return [_grupo(n, muestras[n]) for n in sorted(muestras, key=lambda n: (slug(n), n))]


def _tematicas(
    contadas: list[EvaluacionContada],
    mapeos: dict[int, MapeoVersion | None],
    taxonomia: dict[int, Tematica],
) -> list[DominioGrupo]:
    """Dominio por temática; una temática padre incluye lo de sus subtemas (orden por id)."""
    muestras: dict[int, list[Fraction]] = defaultdict(list)
    for contada in contadas:
        mapeo = mapeos.get(contada.version.id) or {}
        for criterio in contada.criterios:
            valor = muestra(criterio)
            item = mapeo.get(criterio.criterio_id)
            if valor is None or item is None:
                continue
            tocadas: set[int] = set()
            for tid in item.tematica_ids:
                tocadas.update([*ancestros(tid, taxonomia), tid])
            for tid in tocadas:
                muestras[tid].append(valor)
    return [_grupo(taxonomia[t].nombre, muestras[t], t) for t in sorted(muestras)]


def _avisos(
    contadas: list[EvaluacionContada],
    mapeos: dict[int, MapeoVersion | None],
    taxonomia: dict[int, Tematica],
) -> list[str]:
    """Avisos para el usuario si el dominio por temática está incompleto."""
    if not contadas:
        return []
    if not taxonomia:
        return [AVISO_SIN_TAXONOMIA]
    return [AVISO_SIN_MAPEO] if any(mapeos.get(c.version.id) is None for c in contadas) else []


# ---------- Datos para la IA (sin datos personales) ----------


def _nombre(texto: str) -> str:
    """Nombre recortado al límite de DatosDesempeno (1–200 caracteres)."""
    return (texto.strip() or "Sin nombre")[:LIMITE_NOMBRE]


def nombre_laboratorio(contada: EvaluacionContada) -> str:
    """Nombre legible del laboratorio: código y título."""
    return _nombre(f"{contada.laboratorio.codigo} - {contada.laboratorio.titulo}")


def datos_desempeno(informe: Informe) -> dict[str, Any]:
    """DatosDesempeno de Rol 1: solo cifras ya calculadas y nombres académicos."""
    evolucion = informe.evolucion
    return {
        "laboratorios": [
            {
                "laboratorio": nombre_laboratorio(lab.contada),
                "cohorte": _nombre(lab.contada.cohorte.nombre),
                "nota": numero(lab.nota),
            }
            for lab in informe.laboratorios
        ],
        "promedios_cohorte": [
            {"cohorte": _nombre(p.cohorte.nombre), "promedio": numero(p.promedio)}
            for p in informe.promedios_cohorte
        ],
        "promedio_general": numero(informe.promedio_general),
        "tematicas": [
            {
                "tematica": _nombre(g.nombre),
                "promedio": numero(g.promedio),
                "nivel_dominio": g.nivel,
            }
            for g in informe.tematicas
        ],
        "competencias": [
            {
                "competencia": _nombre(g.nombre),
                "promedio": numero(g.promedio),
                "nivel_dominio": g.nivel,
            }
            for g in informe.competencias
        ],
        "evolucion": []
        if evolucion is None
        else [
            {
                "cohorte_inicial": _nombre(evolucion.cohorte_inicial),
                "cohorte_final": _nombre(evolucion.cohorte_final),
                "promedio_inicial": numero(evolucion.promedio_inicial),
                "promedio_final": numero(evolucion.promedio_final),
                "diferencia": numero(evolucion.diferencia),
            }
        ],
    }


# ---------- Narrativa ----------


def _contenido(narrativa: NarrativaIA) -> dict[str, Any]:
    """Solo los textos de la narrativa (lo que se guarda en caché y se devuelve)."""
    return {
        "competencias_desarrolladas": narrativa.competencias_desarrolladas,
        "brechas": narrativa.brechas,
        "plan_fortalecimiento": [
            {
                "accion": a.accion,
                "recurso": a.recurso,
                "prioridad": a.prioridad,
                "competencia": a.competencia,
            }
            for a in narrativa.plan_fortalecimiento
        ],
        "conclusion": narrativa.conclusion,
    }


def _generada(contenido: dict[str, Any], generada_en: datetime | None) -> Narrativa:
    """Narrativa lista para devolver a partir de los textos guardados."""
    return Narrativa(
        estado="generada",
        competencias_desarrolladas=[
            str(t) for t in contenido.get("competencias_desarrolladas", [])
        ],
        brechas=[str(t) for t in contenido.get("brechas", [])],
        plan_fortalecimiento=[
            {k: str(a.get(k, "")) for k in ("accion", "recurso", "prioridad", "competencia")}
            for a in contenido.get("plan_fortalecimiento", [])
        ],
        conclusion=contenido.get("conclusion"),
        generada_en=generada_en,
    )


def _narrativa(
    db: Session,
    informe: Informe,
    ia: IAInforme,
    config: ConfigProveedor,
    perfil: Perfil,
) -> Narrativa:
    """Narrativa desde la caché o generada con IA; nunca lanza (estado error/no_disponible)."""
    if not informe.laboratorios:
        return Narrativa("sin_datos", MSG_SIN_DATOS)
    datos = datos_desempeno(informe)
    clave = str(informe.estudiante.id)
    huella = cache_ia.huella(datos)
    version = ia.version_prompt("informe")
    fila: CacheIA | None = cache_ia.leer(db, TIPO, clave, huella, version)
    if fila is not None:
        return _generada(fila.contenido, fila.generado_en)
    if version is None:
        return Narrativa("no_disponible", MSG_NO_DISPONIBLE)
    try:
        narrativa = ia.narrativa(datos, config)
    except IANoDisponibleError:
        return Narrativa("no_disponible", MSG_NO_DISPONIBLE)
    except Exception as error:  # el detalle solo va a auditoría
        cache_ia.auditar(
            db, perfil.id, "perfiles", clave, "generar_informe_ia_error", detalle_error(error)
        )
        return Narrativa("error", MSG_ERROR)
    contenido = _contenido(narrativa)
    cache_ia.auditar(
        db,
        perfil.id,
        "perfiles",
        clave,
        "generar_informe_ia",
        {
            "proveedor": narrativa.proveedor,
            "modelo": narrativa.modelo,
            "version_prompt": narrativa.version_prompt,
            "huella": huella,
            "respuestas_crudas": narrativa.respuestas_crudas,
        },
    )
    generada_en = cache_ia.guardar(
        db, TIPO, clave, huella, contenido,
        version_prompt=narrativa.version_prompt or version,
        proveedor=narrativa.proveedor,
        modelo=narrativa.modelo,
    )
    return _generada(contenido, generada_en)


def obtener_informe(
    db: Session,
    estudiante_id: uuid.UUID,
    perfil: Perfil,
    ia: IAInforme,
    settings: Settings,
) -> Informe:
    """Informe del estudiante (propio o, para docente/admin, de cualquiera)."""
    estudiante = estudiante_visible(db, estudiante_id, perfil)
    contadas = evaluaciones_contadas(db, estudiante.id)
    laboratorios = [LaboratorioInforme(c, c.evaluacion.nota) for c in contadas]
    taxonomia = cargar_taxonomia(db) if contadas else {}
    config = configuracion_ia(db, settings)
    mapeos = obtener_mapeos(db, [c.version for c in contadas], taxonomia, ia, config, perfil)
    promedios = _promedios_cohorte(db, laboratorios)
    notas = [fraccion(lab.nota) for lab in laboratorios if lab.nota is not None]
    informe = Informe(
        estudiante=estudiante,
        laboratorios=laboratorios,
        promedios_cohorte=promedios,
        promedio_general=promedio(notas),
        competencias=_competencias(contadas),
        tematicas=_tematicas(contadas, mapeos, taxonomia),
        evolucion=_evolucion(promedios),
        narrativa=Narrativa("sin_datos", MSG_SIN_DATOS),
        avisos=_avisos(contadas, mapeos, taxonomia),
    )
    narrativa = _narrativa(db, informe, ia, config, perfil)
    return replace(informe, narrativa=narrativa)
