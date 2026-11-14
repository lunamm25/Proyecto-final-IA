"""Errores de dominio que lanzan los servicios; la capa API los traduce a HTTP."""


class DominioError(Exception):
    """Error de negocio con un mensaje en español para el usuario."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontradoError(DominioError):
    """El recurso pedido no existe (HTTP 404)."""


class ProhibidoError(DominioError):
    """El usuario no puede ver o hacer esto en el estado actual (HTTP 403)."""


class ConflictoError(DominioError):
    """La operación choca con el estado actual de los datos (HTTP 409)."""


class DatosInvalidosError(DominioError):
    """Los datos recibidos no son válidos (HTTP 422)."""


class RubricaConInconsistenciasError(DatosInvalidosError):
    """La rúbrica tiene inconsistencias y no se puede guardar (HTTP 422)."""

    def __init__(self, inconsistencias: list[str]) -> None:
        super().__init__("La rúbrica tiene inconsistencias y no se puede guardar.")
        self.inconsistencias = inconsistencias
