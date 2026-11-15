"""Extracción de la rúbrica de un enunciado en PDF con IA (RF-03 CA1).

Flujo: laboratorio existe → PDF válido (≤ 20 MB, con texto) → la IA propone la rúbrica →
el validador del backend lista las inconsistencias. NO se guarda nada salvo la auditoría:
el docente revisa y edita la propuesta y la guarda con POST .../rubrica/versiones.
Cualquier fallo de la IA se resume en un mensaje genérico; el detalle tachado va a auditoría.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Auditoria, Laboratorio, Perfil
from app.services.archivos import ArchivoEntrada, MensajesPdf, validar_pdf
from app.services.errores import NoEncontradoError, ServicioNoDisponibleError
from app.services.evaluaciones import configuracion_ia
from app.services.extractor_rubrica import ExtractorRubrica
from app.services.material import extraer_texto_pdf
from app.services.rubricas import MSG_LAB_NO_EXISTE, validar_rubrica
from app.services.secretos import detalle_error_tachado

LIMITE_TEXTO_ENUNCIADO = 100_000  # caracteres enviados a la IA (evita prompts enormes)
LIMITE_MENSAJE_AUDITORIA = 4_000
ACCION_EXITO = "extraer_rubrica_ia"
ACCION_ERROR = "extraer_rubrica_ia_error"
MSG_ERROR_IA = (
    "No se pudo extraer la rúbrica automáticamente. Inténtalo de nuevo o créala a mano."
)
MENSAJES_PDF = MensajesPdf(
    grande="El PDF del enunciado supera el tamaño máximo de 20 MB.",
    tipo="El archivo del enunciado no es un PDF válido.",
    ilegible="El PDF del enunciado está dañado o protegido y no se puede leer.",
    sin_texto=(
        "El PDF no tiene texto extraíble (¿es un escaneo o una imagen?). "
        "Sube un PDF con texto seleccionable o crea la rúbrica a mano."
    ),
)


@dataclass(frozen=True)
class PropuestaRubrica:
    """Rúbrica propuesta por la IA y el resultado del validador (no se guarda)."""

    rubrica: dict[str, Any]
    inconsistencias: list[str]

    @property
    def valida(self) -> bool:
        """True si el validador no encontró inconsistencias."""
        return not self.inconsistencias


def leer_pdf_enunciado(archivo: ArchivoEntrada) -> bytes:
    """Bytes del PDF del enunciado ya validado (tipo, tamaño por bloques y texto)."""
    return validar_pdf(archivo, MENSAJES_PDF)


def _auditar(db: Session, actor: Perfil, laboratorio_id: int, accion: str, datos: dict) -> None:
    """Añade el registro de auditoría y confirma la transacción."""
    db.add(
        Auditoria(
            usuario_id=actor.id,
            entidad="laboratorios",
            entidad_id=str(laboratorio_id),
            accion=accion,
            despues={"laboratorio_id": laboratorio_id, **datos},
        )
    )
    db.commit()


def extraer_de_pdf(
    db: Session,
    laboratorio_id: int,
    archivo: ArchivoEntrada,
    actor: Perfil,
    settings: Settings,
    extractor: ExtractorRubrica,
) -> PropuestaRubrica:
    """Propone la rúbrica del enunciado en PDF y la valida; solo deja huella en auditoría."""
    if db.get(Laboratorio, laboratorio_id) is None:
        raise NoEncontradoError(MSG_LAB_NO_EXISTE)
    datos = leer_pdf_enunciado(archivo)
    texto = extraer_texto_pdf(datos, limite=LIMITE_TEXTO_ENUNCIADO)[:LIMITE_TEXTO_ENUNCIADO]
    config = configuracion_ia(db, settings)
    base = {"proveedor": config.proveedor, "modelo": config.modelo, "tamano_pdf_bytes": len(datos)}
    try:
        extraida = extractor(texto, config)
    except Exception as error:  # cualquier fallo de la IA: mensaje genérico al cliente
        detalle = detalle_error_tachado(error, settings, LIMITE_MENSAJE_AUDITORIA)
        _auditar(db, actor, laboratorio_id, ACCION_ERROR, {**base, "error": detalle})
        raise ServicioNoDisponibleError(MSG_ERROR_IA) from None
    inconsistencias = validar_rubrica(extraida.rubrica)
    criterios = extraida.rubrica.get("criterios") if isinstance(extraida.rubrica, dict) else None
    _auditar(
        db,
        actor,
        laboratorio_id,
        ACCION_EXITO,
        {
            **base,
            "version_prompt": extraida.version_prompt,
            "criterios": len(criterios) if isinstance(criterios, list) else 0,
            "valida": not inconsistencias,
            "inconsistencias": len(inconsistencias),
            "respuestas_crudas": list(extraida.respuestas_crudas),
        },
    )
    return PropuestaRubrica(extraida.rubrica, inconsistencias)
