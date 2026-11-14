"""Mapa de conocimiento del estudiante (RF-09 CA3): grafo {nodos, aristas}.

Estructura: temática → subtemas (por `padre_id`) → conceptos → laboratorios donde se aplicó.
Solo usa evaluaciones publicadas (la que cuenta por laboratorio, ver desempeno.py).
- Dominio de un nodo temática/concepto = promedio de normalizado × 5 de los criterios asociados
  (una temática padre incluye los de sus subtemas); nivel bajo/medio/alto como en desempeno.py.
- Dominio de un nodo laboratorio = la nota de ese laboratorio.
- Evidencias: solo citas verificadas. Aspectos por profundizar: debilidades y recomendación del
  criterio (texto editado por el docente si existe) y, en el laboratorio, los aspectos a fortalecer.
Si una versión de rúbrica no tiene mapeo (IA no disponible o con error), sus criterios se agrupan
por competencia: competencia → criterio → laboratorio.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Perfil, Tematica
from app.services.desempeno import (
    CriterioContado,
    EvaluacionContada,
    dominio,
    estudiante_visible,
    evaluaciones_contadas,
    muestra,
    nivel_dominio,
)
from app.services.evaluaciones import configuracion_ia
from app.services.informe_ia import IAInforme
from app.services.mapeo_tematicas import (
    MapeoVersion,
    ancestros,
    cargar_taxonomia,
    obtener_mapeos,
    slug,
)
from app.services.revision import retro_criterio_final, retro_general_final

MAX_EVIDENCIAS = 10
MAX_ASPECTOS = 10
AVISO_SIN_MAPEO = (
    "Algunos criterios no se pudieron asociar con temáticas con IA; se muestran agrupados por "
    "competencia."
)


@dataclass
class Nodo:
    """Nodo del grafo con lo acumulado de los criterios que lo alimentan."""

    id: str
    tipo: str
    etiqueta: str
    muestras: list[Fraction] = field(default_factory=list)
    nota: Decimal | None = None
    evidencias: list[dict[str, Any]] = field(default_factory=list)
    aspectos: list[str] = field(default_factory=list)
    laboratorios: list[str] = field(default_factory=list)

    @property
    def dominio(self) -> Decimal | None:
        """Nota del laboratorio o promedio de las muestras (0–5, 1 decimal)."""
        return self.nota if self.tipo == "laboratorio" else dominio(self.muestras)

    @property
    def nivel(self) -> str | None:
        """bajo / medio / alto según el dominio."""
        return nivel_dominio(self.dominio)


@dataclass(frozen=True)
class Arista:
    """Relación padre → hijo."""

    origen: str
    destino: str


@dataclass(frozen=True)
class Mapa:
    """Grafo listo para el frontend y avisos para el usuario."""

    nodos: list[Nodo]
    aristas: list[Arista]
    avisos: list[str]


@dataclass(frozen=True)
class Aporte:
    """Lo que un criterio de un laboratorio aporta a los nodos que toca."""

    muestra: Fraction | None
    evidencias: list[dict[str, Any]]
    aspectos: list[str]
    laboratorio: str


def _agregar_unicos(destino: list[Any], nuevos: list[Any], maximo: int) -> None:
    """Agrega sin repetir y sin pasar del máximo."""
    for item in nuevos:
        if len(destino) >= maximo:
            return
        if item not in destino:
            destino.append(item)


class Grafo:
    """Construye nodos y aristas sin duplicados, en orden de aparición."""

    def __init__(self) -> None:
        self.nodos: dict[str, Nodo] = {}
        self.aristas: dict[tuple[str, str], Arista] = {}

    def nodo(self, nodo_id: str, tipo: str, etiqueta: str) -> Nodo:
        """Devuelve el nodo, creándolo si no existe."""
        if nodo_id not in self.nodos:
            self.nodos[nodo_id] = Nodo(nodo_id, tipo, etiqueta)
        return self.nodos[nodo_id]

    def arista(self, origen: str, destino: str) -> None:
        """Agrega la arista si no existe."""
        self.aristas.setdefault((origen, destino), Arista(origen, destino))

    def aportar(self, nodo: Nodo, aporte: Aporte) -> None:
        """Suma la muestra, evidencias, aspectos y laboratorio de un criterio al nodo."""
        if aporte.muestra is not None:
            nodo.muestras.append(aporte.muestra)
        _agregar_unicos(nodo.evidencias, aporte.evidencias, MAX_EVIDENCIAS)
        _agregar_unicos(nodo.aspectos, aporte.aspectos, MAX_ASPECTOS)
        if aporte.laboratorio not in nodo.laboratorios:
            nodo.laboratorios.append(aporte.laboratorio)


def _evidencias(criterio: CriterioContado, codigo: str) -> list[dict[str, Any]]:
    """Citas verificadas del criterio, sin datos internos del modelo (similitud, nivel IA)."""
    return [
        {
            "fragmento": str(cita.get("fragmento", "")),
            "fuente": str(cita.get("fuente", "")),
            "ubicacion": cita.get("ubicacion"),
            "laboratorio": codigo,
            "criterio_id": criterio.criterio_id,
        }
        for cita in criterio.fila.evidencias_verificadas or []
        if isinstance(cita, dict) and cita.get("verificada") is True
    ]


def _aspectos(criterio: CriterioContado, contada: EvaluacionContada) -> list[str]:
    """Debilidades y recomendación finales del criterio (edición del docente si existe)."""
    final = retro_criterio_final(criterio.fila, contada.evaluacion)
    textos = [str(d) for d in final.get("debilidades") or []]
    if final.get("recomendacion"):
        textos.append(str(final["recomendacion"]))
    return [t for t in textos if t.strip()]


def _por_tematicas(
    grafo: Grafo,
    lab_id: str,
    item_tematicas: list[int],
    conceptos: list[str],
    taxonomia: dict[int, Tematica],
) -> set[str]:
    """Crea temática → subtemas → conceptos → laboratorio; devuelve los nodos tocados."""
    tocados: set[str] = set()
    for tid in item_tematicas:
        anterior = None
        for actual in [*ancestros(tid, taxonomia), tid]:
            tematica = taxonomia[actual]
            tipo = "subtema" if tematica.padre_id in taxonomia else "tematica"
            grafo.nodo(f"tematica:{actual}", tipo, tematica.nombre)
            tocados.add(f"tematica:{actual}")
            if anterior is not None:
                grafo.arista(anterior, f"tematica:{actual}")
            anterior = f"tematica:{actual}"
        for concepto in conceptos:
            concepto_id = f"concepto:{tid}:{slug(concepto)}"
            grafo.nodo(concepto_id, "concepto", concepto)
            tocados.add(concepto_id)
            grafo.arista(f"tematica:{tid}", concepto_id)
            grafo.arista(concepto_id, lab_id)
    return tocados


def _por_competencia(grafo: Grafo, lab_id: str, criterio: CriterioContado) -> set[str]:
    """Alternativa sin mapeo: competencia → criterio → laboratorio."""
    clave = slug(criterio.competencia)
    competencia_id = f"competencia:{clave}"
    concepto_id = f"concepto:competencia-{clave}:{slug(criterio.nombre)}"
    grafo.nodo(competencia_id, "competencia", criterio.competencia)
    grafo.nodo(concepto_id, "concepto", criterio.nombre)
    grafo.arista(competencia_id, concepto_id)
    grafo.arista(concepto_id, lab_id)
    return {competencia_id, concepto_id}


def _laboratorio(grafo: Grafo, contada: EvaluacionContada) -> str:
    """Nodo del laboratorio con su nota, citas verificadas y aspectos a fortalecer."""
    codigo = contada.laboratorio.codigo
    lab = grafo.nodo(f"lab:{codigo}", "laboratorio", f"{codigo} · {contada.laboratorio.titulo}")
    lab.nota = contada.evaluacion.nota
    general = retro_general_final(contada.evaluacion).get("aspectos_a_fortalecer") or []
    evidencias = [e for c in contada.criterios for e in _evidencias(c, codigo)]
    grafo.aportar(lab, Aporte(None, evidencias, [str(a) for a in general], codigo))
    return lab.id


def construir_mapa(
    contadas: list[EvaluacionContada],
    mapeos: dict[int, MapeoVersion | None],
    taxonomia: dict[int, Tematica],
) -> Mapa:
    """Grafo a partir de las evaluaciones que cuentan y del mapeo de cada versión de rúbrica."""
    grafo = Grafo()
    sin_mapeo = False
    for contada in contadas:
        lab_id = _laboratorio(grafo, contada)
        mapeo = mapeos.get(contada.version.id)
        sin_mapeo = sin_mapeo or mapeo is None
        for criterio in contada.criterios:
            item = (mapeo or {}).get(criterio.criterio_id)
            if item is not None and item.tematica_ids:
                conceptos = item.conceptos or [criterio.nombre]
                tocados = _por_tematicas(grafo, lab_id, item.tematica_ids, conceptos, taxonomia)
            else:
                tocados = _por_competencia(grafo, lab_id, criterio)
            aporte = Aporte(
                muestra(criterio),
                _evidencias(criterio, contada.laboratorio.codigo),
                _aspectos(criterio, contada),
                contada.laboratorio.codigo,
            )
            for nodo_id in tocados:
                grafo.aportar(grafo.nodos[nodo_id], aporte)
    avisos = [AVISO_SIN_MAPEO] if sin_mapeo else []
    return Mapa(list(grafo.nodos.values()), list(grafo.aristas.values()), avisos)


def obtener_mapa(
    db: Session, estudiante_id: uuid.UUID, perfil: Perfil, ia: IAInforme, settings: Settings
) -> Mapa:
    """Mapa del estudiante (propio o, para docente/admin, de cualquiera); vacío sin publicadas."""
    estudiante = estudiante_visible(db, estudiante_id, perfil)
    contadas = evaluaciones_contadas(db, estudiante.id)
    if not contadas:
        return Mapa([], [], [])
    taxonomia = cargar_taxonomia(db)
    config = configuracion_ia(db, settings)
    mapeos = obtener_mapeos(db, [c.version for c in contadas], taxonomia, ia, config, perfil)
    return construir_mapa(contadas, mapeos, taxonomia)
