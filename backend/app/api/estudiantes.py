"""Rutas de estudiantes: listado docente, informe integrado (RF-08) y mapa (RF-09)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import UsuarioActual, obtener_ia_informe, requiere_rol
from app.api.esquemas import (
    AristaMapaRespuesta,
    CompetenciaInformeRespuesta,
    ErrorRespuesta,
    EstudianteListado,
    EstudianteResumen,
    EvidenciaMapaRespuesta,
    EvolucionRespuesta,
    InformeRespuesta,
    LaboratorioInformeRespuesta,
    ListadoEstudiantesRespuesta,
    MapaRespuesta,
    NarrativaRespuesta,
    NodoMapaRespuesta,
    PromedioCohorteRespuesta,
    TematicaInformeRespuesta,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Perfil
from app.services import estudiantes as servicio
from app.services.desempeno import numero
from app.services.informe import Informe, obtener_informe
from app.services.informe_ia import IAInforme
from app.services.mapa import Mapa, obtener_mapa
from app.services.traza import a_utc

router = APIRouter(prefix="/api/estudiantes", tags=["estudiantes"])

BaseDatos = Annotated[Session, Depends(get_db)]
Docente = Annotated[Perfil, Depends(requiere_rol("docente"))]
IA = Annotated[IAInforme, Depends(obtener_ia_informe)]
Ajustes = Annotated[Settings, Depends(get_settings)]

LIMIT_POR_DEFECTO = 20
LIMIT_MAXIMO = 100

RESPUESTAS_LISTADO = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    403: {"model": ErrorRespuesta, "description": "Solo docente o administrador"},
    422: {"model": ErrorRespuesta, "description": "Paginación no válida"},
}
RESPUESTAS_ESTUDIANTE = {
    401: {"model": ErrorRespuesta, "description": "No autenticado"},
    404: {"model": ErrorRespuesta, "description": "Estudiante no encontrado (u otro estudiante)"},
    422: {"model": ErrorRespuesta, "description": "Id no válido"},
}


@router.get("", response_model=ListadoEstudiantesRespuesta, responses=RESPUESTAS_LISTADO)
def listar_estudiantes(
    _docente: Docente,
    db: BaseDatos,
    limit: int = Query(default=LIMIT_POR_DEFECTO, ge=1, le=LIMIT_MAXIMO),
    offset: int = Query(default=0, ge=0),
) -> ListadoEstudiantesRespuesta:
    """Estudiantes por nombre con sus laboratorios evaluados (publicados), paginado."""
    pagina = servicio.listar_estudiantes(db, limit=limit, offset=offset)
    return ListadoEstudiantesRespuesta(
        items=[
            EstudianteListado(
                id=f.perfil.id,
                nombre=f.perfil.nombre,
                correo=f.perfil.correo,
                laboratorios_evaluados=f.laboratorios_evaluados,
            )
            for f in pagina.filas
        ],
        total=pagina.total,
        limit=limit,
        offset=offset,
    )


def _informe(informe: Informe) -> InformeRespuesta:
    """Convierte el informe del servicio en la respuesta (números y narrativa por separado)."""
    evolucion = informe.evolucion
    narrativa = informe.narrativa
    return InformeRespuesta(
        estudiante=EstudianteResumen(id=informe.estudiante.id, nombre=informe.estudiante.nombre),
        laboratorios_evaluados=len(informe.laboratorios),
        laboratorios=[
            LaboratorioInformeRespuesta(
                laboratorio_id=lab.contada.laboratorio.id,
                codigo=lab.contada.laboratorio.codigo,
                titulo=lab.contada.laboratorio.titulo,
                cohorte=lab.contada.cohorte.nombre,
                cohorte_numero=lab.contada.cohorte.numero,
                nota=numero(lab.nota),
                evaluacion_id=lab.contada.evaluacion.id,
                publicada_en=a_utc(lab.contada.evaluacion.publicada_en),
            )
            for lab in informe.laboratorios
        ],
        promedios_cohorte=[
            PromedioCohorteRespuesta(
                cohorte=p.cohorte.nombre,
                cohorte_numero=p.cohorte.numero,
                promedio=numero(p.promedio),
                laboratorios_evaluados=p.laboratorios_evaluados,
            )
            for p in informe.promedios_cohorte
        ],
        promedio_general=numero(informe.promedio_general),
        competencias=[
            CompetenciaInformeRespuesta(
                competencia=g.nombre,
                promedio=numero(g.promedio),
                nivel_dominio=g.nivel,
                criterios_evaluados=g.criterios_evaluados,
            )
            for g in informe.competencias
        ],
        tematicas=[
            TematicaInformeRespuesta(
                tematica_id=g.tematica_id,
                tematica=g.nombre,
                promedio=numero(g.promedio),
                nivel_dominio=g.nivel,
                criterios_evaluados=g.criterios_evaluados,
            )
            for g in informe.tematicas
        ],
        evolucion=None
        if evolucion is None
        else EvolucionRespuesta(
            cohorte_inicial=evolucion.cohorte_inicial,
            cohorte_final=evolucion.cohorte_final,
            promedio_inicial=numero(evolucion.promedio_inicial),
            promedio_final=numero(evolucion.promedio_final),
            diferencia=numero(evolucion.diferencia),
        ),
        narrativa=NarrativaRespuesta(
            estado=narrativa.estado,
            mensaje=narrativa.mensaje,
            competencias_desarrolladas=narrativa.competencias_desarrolladas,
            brechas=narrativa.brechas,
            plan_fortalecimiento=narrativa.plan_fortalecimiento,
            conclusion=narrativa.conclusion,
            generada_en=a_utc(narrativa.generada_en),
        ),
        avisos=informe.avisos,
    )


def _mapa(mapa: Mapa) -> MapaRespuesta:
    """Convierte el grafo del servicio en la respuesta."""
    return MapaRespuesta(
        nodos=[
            NodoMapaRespuesta(
                id=n.id,
                tipo=n.tipo,
                etiqueta=n.etiqueta,
                dominio=numero(n.dominio),
                nivel_dominio=n.nivel,
                evidencias=[EvidenciaMapaRespuesta.model_validate(e) for e in n.evidencias],
                aspectos_por_profundizar=n.aspectos,
                laboratorios=n.laboratorios,
            )
            for n in mapa.nodos
        ],
        aristas=[AristaMapaRespuesta(origen=a.origen, destino=a.destino) for a in mapa.aristas],
        avisos=mapa.avisos,
    )


@router.get(
    "/{estudiante_id}/informe", response_model=InformeRespuesta, responses=RESPUESTAS_ESTUDIANTE
)
def ver_informe(
    estudiante_id: uuid.UUID, perfil: UsuarioActual, db: BaseDatos, ia: IA, settings: Ajustes
) -> InformeRespuesta:
    """Informe integrado: el propio estudiante o docente/admin. Solo evaluaciones publicadas."""
    return _informe(obtener_informe(db, estudiante_id, perfil, ia, settings))


@router.get("/{estudiante_id}/mapa", response_model=MapaRespuesta, responses=RESPUESTAS_ESTUDIANTE)
def ver_mapa(
    estudiante_id: uuid.UUID, perfil: UsuarioActual, db: BaseDatos, ia: IA, settings: Ajustes
) -> MapaRespuesta:
    """Mapa de conocimiento {nodos, aristas}: el propio estudiante o docente/admin."""
    return _mapa(obtener_mapa(db, estudiante_id, perfil, ia, settings))
