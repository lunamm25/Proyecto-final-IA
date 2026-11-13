"""Validación del JWT de Supabase (HS256 con secreto o ES256/RS256 con JWKS)."""

import uuid
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from app.config import Settings

AUDIENCIA = "authenticated"
ALGORITMOS_ASIMETRICOS = frozenset({"ES256", "RS256"})
ALGORITMO_SECRETO = "HS256"
MARGEN_SEGUNDOS = 10
MENSAJE_TOKEN_INVALIDO = "Token inválido o expirado. Vuelve a iniciar sesión."
MENSAJE_TIPO_NO_ACEPTADO = "El servidor no acepta este tipo de token."


class TokenInvalidoError(Exception):
    """Token ausente, mal formado o inválido (se traduce a HTTP 401)."""

    def __init__(self, mensaje: str = MENSAJE_TOKEN_INVALIDO) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


def base_supabase(settings: Settings) -> str:
    """URL de Supabase sin barra final (vacía si no está configurada)."""
    return settings.supabase_url.strip().rstrip("/")


@lru_cache
def _cliente_jwks(url: str) -> PyJWKClient:
    """Crea una sola vez (por URL) el cliente JWKS con caché de claves."""
    return PyJWKClient(url, cache_keys=True, lifespan=600, timeout=5)


def obtener_clave_jwks(token: str, settings: Settings) -> Any:
    """Obtiene (con caché) la clave pública del JWKS de Supabase según el `kid`."""
    base = base_supabase(settings)
    if not base:
        raise TokenInvalidoError(MENSAJE_TIPO_NO_ACEPTADO)
    try:
        cliente = _cliente_jwks(f"{base}/auth/v1/.well-known/jwks.json")
        return cliente.get_signing_key_from_jwt(token).key
    except Exception as error:  # red caída, kid desconocido, JWKS mal formado...
        raise TokenInvalidoError() from error


def _clave_para(token: str, alg: str, settings: Settings) -> Any:
    """Elige la clave de verificación según el algoritmo (lista blanca explícita)."""
    if alg == ALGORITMO_SECRETO:
        if not settings.supabase_jwt_secret:
            raise TokenInvalidoError(MENSAJE_TIPO_NO_ACEPTADO)
        return settings.supabase_jwt_secret
    if alg in ALGORITMOS_ASIMETRICOS:
        return obtener_clave_jwks(token, settings)
    raise TokenInvalidoError()


def validar_token(token: str, settings: Settings) -> uuid.UUID:
    """Verifica firma, exp, aud, iss y sub; devuelve el id (uuid) del usuario."""
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except Exception as error:  # cabecera ilegible
        raise TokenInvalidoError() from error
    if not isinstance(alg, str):
        raise TokenInvalidoError()
    clave = _clave_para(token, alg, settings)
    base = base_supabase(settings)
    requeridos = ["exp", "sub", "aud"] + (["iss"] if base else [])
    try:
        claims = jwt.decode(
            token,
            clave,
            algorithms=[alg],
            audience=AUDIENCIA,
            issuer=f"{base}/auth/v1" if base else None,
            leeway=MARGEN_SEGUNDOS,
            options={"require": requeridos},
        )
        return uuid.UUID(str(claims["sub"]))
    except Exception as error:  # firma, expiración, audiencia, sub no-uuid, clave rara...
        raise TokenInvalidoError() from error
