"""Pruebas de autenticación (JWT de Supabase), permisos por rol, GET /api/yo y CORS."""

import base64
import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Iterator
from typing import Annotated

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import requiere_rol
from app.config import Settings, get_settings
from app.db import Base, get_db
from app.main import crear_app
from app.models import Perfil
from app.services import auth

SECRETO = "secreto-de-prueba-inventado-y-largo-para-hmac-0123456789abcdefghijklmnopqrstuvwxyz"
URL_SUPABASE = "https://proyecto-falso.supabase.co"
EMISOR = f"{URL_SUPABASE}/auth/v1"
ID_ESTUDIANTE = uuid.UUID("11111111-1111-1111-1111-111111111111")
ID_DOCENTE = uuid.UUID("22222222-2222-2222-2222-222222222222")
ID_ADMIN = uuid.UUID("33333333-3333-3333-3333-333333333333")
ID_SIN_PERFIL = uuid.UUID("44444444-4444-4444-4444-444444444444")
CLAVE_EC = ec.generate_private_key(ec.SECP256R1())
CLAVE_RSA = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def ajustes(**cambios: str) -> Settings:
    """Settings inventados para los tests (sin leer .env)."""
    valores = {"supabase_url": URL_SUPABASE, "supabase_jwt_secret": SECRETO}
    valores.update(cambios)
    return Settings(_env_file=None, **valores)


def claims(sub: uuid.UUID | str = ID_ESTUDIANTE, **cambios: object) -> dict[str, object]:
    """Claims típicos de un access_token de Supabase."""
    datos: dict[str, object] = {
        "sub": str(sub),
        "aud": "authenticated",
        "iss": EMISOR,
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    datos.update(cambios)
    return {k: v for k, v in datos.items() if v is not None}


def token_hs(
    sub: uuid.UUID | str = ID_ESTUDIANTE, secreto: str = SECRETO, **cambios: object
) -> str:
    """Token HS256 firmado con el secreto indicado."""
    return jwt.encode(claims(sub, **cambios), secreto, algorithm="HS256")


def b64(datos: bytes) -> str:
    """Base64url sin relleno."""
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def token_manual(cabecera: dict[str, object], cuerpo: dict[str, object], clave: bytes) -> str:
    """Construye un JWT a mano firmado con HMAC-SHA256 (o sin firma si clave vacía)."""
    inicio = f"{b64(json.dumps(cabecera).encode())}.{b64(json.dumps(cuerpo).encode())}"
    firma = hmac.new(clave, inicio.encode(), hashlib.sha256).digest() if clave else b""
    return f"{inicio}.{b64(firma)}"


def pem_publica(clave_privada) -> bytes:
    """Clave pública en PEM."""
    return clave_privada.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


@pytest.fixture
def sesion_compartida() -> Iterator[sessionmaker[Session]]:
    """SQLite en memoria compartida entre hilos con perfiles de cada rol."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)
    with fabrica() as s:
        s.add_all(
            [
                Perfil(id=ID_ESTUDIANTE, nombre="Ana Estudiante", rol="estudiante"),
                Perfil(id=ID_DOCENTE, nombre="Diego Docente", rol="docente", foto_url="f.png"),
                Perfil(id=ID_ADMIN, nombre="Alba Admin", rol="admin"),
            ]
        )
        s.commit()
    yield fabrica
    engine.dispose()


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Falla si algún test intenta crear el cliente JWKS real (llamada de red)."""

    def _prohibido(*_args, **_kwargs):
        raise AssertionError("No se permite crear PyJWKClient en los tests")

    auth._cliente_jwks.cache_clear()
    monkeypatch.setattr(auth, "PyJWKClient", _prohibido)
    yield
    auth._cliente_jwks.cache_clear()


def preparar(app: FastAPI, fabrica: sessionmaker[Session], settings: Settings) -> TestClient:
    """Sustituye BD y configuración por las de prueba."""

    def _db() -> Iterator[Session]:
        with fabrica() as s:
            yield s

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture
def cliente(sesion_compartida) -> TestClient:
    """Cliente de la app real con HS256 y JWKS configurados."""
    return preparar(crear_app(ajustes()), sesion_compartida, ajustes())


def con_token(token: str) -> dict[str, str]:
    """Encabezado Authorization Bearer."""
    return {"Authorization": f"Bearer {token}"}


def jwks_falso(monkeypatch, clave_publica, kid: str = "kid-1") -> None:
    """Sustituye la obtención de clave JWKS por una clave local (sin red)."""

    def _obtener(token: str, _settings: Settings):
        if jwt.get_unverified_header(token).get("kid") != kid:
            raise auth.TokenInvalidoError()
        return clave_publica

    monkeypatch.setattr(auth, "obtener_clave_jwks", _obtener)


def assert_401(respuesta, *secretos: str) -> None:
    """401 en español, con WWW-Authenticate y sin filtrar token ni secreto."""
    assert respuesta.status_code == 401
    assert respuesta.headers.get("www-authenticate") == "Bearer"
    detalle = respuesta.json()["detail"]
    assert isinstance(detalle, str) and detalle
    for valor in (SECRETO, *secretos):
        assert valor not in respuesta.text


# ---------- Tokens válidos ----------


def test_hs256_valido_devuelve_perfil(cliente):
    r = cliente.get("/api/yo", headers=con_token(token_hs(ID_DOCENTE)))
    assert r.status_code == 200
    assert r.json() == {
        "id": str(ID_DOCENTE),
        "nombre": "Diego Docente",
        "rol": "docente",
        "foto_url": "f.png",
    }


def test_es256_valido_con_jwks_falso(cliente, monkeypatch):
    jwks_falso(monkeypatch, CLAVE_EC.public_key())
    token = jwt.encode(claims(), CLAVE_EC, algorithm="ES256", headers={"kid": "kid-1"})
    r = cliente.get("/api/yo", headers=con_token(token))
    assert r.status_code == 200
    assert r.json()["rol"] == "estudiante"


def test_rs256_valido_con_jwks_falso(cliente, monkeypatch):
    jwks_falso(monkeypatch, CLAVE_RSA.public_key())
    token = jwt.encode(claims(ID_ADMIN), CLAVE_RSA, algorithm="RS256", headers={"kid": "kid-1"})
    assert cliente.get("/api/yo", headers=con_token(token)).json()["rol"] == "admin"


def test_rol_sale_de_perfiles_no_del_token(cliente):
    token = token_hs(ID_ESTUDIANTE, role="admin", user_role="docente")
    assert cliente.get("/api/yo", headers=con_token(token)).json()["rol"] == "estudiante"


def test_exp_dentro_del_margen_se_acepta(cliente):
    token = token_hs(exp=int(time.time()) - 5)
    assert cliente.get("/api/yo", headers=con_token(token)).status_code == 200


# ---------- Header ausente o mal formado ----------


def test_sin_header_401(cliente):
    assert_401(cliente.get("/api/yo"))


def test_esquema_distinto_a_bearer_401(cliente):
    token = token_hs()
    assert_401(cliente.get("/api/yo", headers={"Authorization": f"Basic {token}"}), token)


def test_bearer_vacio_401(cliente):
    assert_401(cliente.get("/api/yo", headers={"Authorization": "Bearer "}))


def test_token_basura_401(cliente):
    assert_401(cliente.get("/api/yo", headers=con_token("esto.no.es-un-jwt")), "esto.no.es-un-jwt")


# ---------- Algoritmos ----------


def test_alg_none_401(cliente):
    token = token_manual({"alg": "none", "typ": "JWT"}, claims(), b"")
    assert_401(cliente.get("/api/yo", headers=con_token(token)), token)


def test_alg_none_sin_firma_ni_punto_final_401(cliente):
    token = token_manual({"alg": "none"}, claims(), b"").rstrip(".")
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


@pytest.mark.parametrize("alg", ["HS512", "HS384"])
def test_algoritmo_hmac_no_permitido_401(cliente, alg):
    token = jwt.encode(claims(), SECRETO, algorithm=alg)
    assert_401(cliente.get("/api/yo", headers=con_token(token)), token)


def test_algoritmo_es384_no_permitido_401(cliente, monkeypatch):
    clave = ec.generate_private_key(ec.SECP384R1())
    jwks_falso(monkeypatch, clave.public_key())
    token = jwt.encode(claims(), clave, algorithm="ES384", headers={"kid": "kid-1"})
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


def test_confusion_hs256_firmado_con_clave_publica_401(cliente, monkeypatch):
    jwks_falso(monkeypatch, CLAVE_RSA.public_key())
    token = token_manual(
        {"alg": "HS256", "typ": "JWT", "kid": "kid-1"}, claims(), pem_publica(CLAVE_RSA)
    )
    assert_401(cliente.get("/api/yo", headers=con_token(token)), token)


@pytest.mark.parametrize("alg", ["RS256", "ES256"])
def test_confusion_alg_asimetrico_firmado_con_hmac_401(cliente, monkeypatch, alg):
    clave = CLAVE_RSA if alg == "RS256" else CLAVE_EC
    jwks_falso(monkeypatch, clave.public_key())
    for secreto in (SECRETO.encode(), pem_publica(clave)):
        token = token_manual({"alg": alg, "typ": "JWT", "kid": "kid-1"}, claims(), secreto)
        assert_401(cliente.get("/api/yo", headers=con_token(token)), token)


# ---------- Firma y claims ----------


def test_firma_con_otro_secreto_401(cliente):
    otro = "otro-secreto-distinto-tambien-largo-0123456789abcdef"
    assert_401(cliente.get("/api/yo", headers=con_token(token_hs(secreto=otro))), otro)


def test_token_expirado_401(cliente):
    token = token_hs(exp=int(time.time()) - 120)
    assert_401(cliente.get("/api/yo", headers=con_token(token)), token)


def test_sin_exp_401(cliente):
    token = jwt.encode({k: v for k, v in claims().items() if k != "exp"}, SECRETO, "HS256")
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


@pytest.mark.parametrize("aud", ["anon", "otra-app"])
def test_audiencia_incorrecta_401(cliente, aud):
    assert_401(cliente.get("/api/yo", headers=con_token(token_hs(aud=aud))))


def test_sin_audiencia_401(cliente):
    token = jwt.encode({k: v for k, v in claims().items() if k != "aud"}, SECRETO, "HS256")
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


def test_sin_sub_401(cliente):
    token = jwt.encode({k: v for k, v in claims().items() if k != "sub"}, SECRETO, "HS256")
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


def test_sub_no_uuid_401(cliente):
    assert_401(cliente.get("/api/yo", headers=con_token(token_hs(sub="no-es-un-uuid"))))


def test_emisor_incorrecto_401(cliente):
    token = token_hs(iss="https://otro-proyecto.supabase.co/auth/v1")
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


def test_sin_emisor_401_cuando_hay_supabase_url(cliente):
    token = jwt.encode({k: v for k, v in claims().items() if k != "iss"}, SECRETO, "HS256")
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


def test_url_supabase_con_barra_final_valida_emisor(sesion_compartida):
    s = ajustes(supabase_url=URL_SUPABASE + "/")
    c = preparar(crear_app(s), sesion_compartida, s)
    assert c.get("/api/yo", headers=con_token(token_hs())).status_code == 200


# ---------- Configuración y JWKS ----------


def test_hs256_sin_secreto_configurado_401(sesion_compartida):
    s = ajustes(supabase_jwt_secret="")
    c = preparar(crear_app(s), sesion_compartida, s)
    assert_401(c.get("/api/yo", headers=con_token(token_hs())))


def test_fallo_al_obtener_jwks_401(cliente, monkeypatch):
    class ClienteQueFalla:
        def __init__(self, *_args, **_kwargs):
            pass

        def get_signing_key_from_jwt(self, _token):
            raise jwt.PyJWKClientConnectionError("sin conexión")

    monkeypatch.setattr(auth, "PyJWKClient", ClienteQueFalla)
    token = jwt.encode(claims(), CLAVE_EC, algorithm="ES256", headers={"kid": "kid-1"})
    assert_401(cliente.get("/api/yo", headers=con_token(token)), token)


def test_jwks_usa_url_correcta_y_cliente_cacheado(cliente, monkeypatch):
    urls: list[str] = []

    class ClienteFalso:
        def __init__(self, url, **_kwargs):
            urls.append(url)

        def get_signing_key_from_jwt(self, _token):
            return jwt.PyJWK.from_dict(
                json.loads(jwt.algorithms.ECAlgorithm.to_jwk(CLAVE_EC.public_key()))
                | {"alg": "ES256"}
            )

    monkeypatch.setattr(auth, "PyJWKClient", ClienteFalso)
    token = jwt.encode(claims(), CLAVE_EC, algorithm="ES256", headers={"kid": "kid-1"})
    for _ in range(2):
        assert cliente.get("/api/yo", headers=con_token(token)).status_code == 200
    assert urls == [f"{URL_SUPABASE}/auth/v1/.well-known/jwks.json"]


def test_kid_desconocido_401(cliente, monkeypatch):
    jwks_falso(monkeypatch, CLAVE_EC.public_key(), kid="kid-1")
    token = jwt.encode(claims(), CLAVE_EC, algorithm="ES256", headers={"kid": "kid-otro"})
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


def test_asimetrico_sin_supabase_url_401(sesion_compartida):
    s = ajustes(supabase_url="")
    c = preparar(crear_app(s), sesion_compartida, s)
    token = jwt.encode(claims(), CLAVE_EC, algorithm="ES256", headers={"kid": "kid-1"})
    assert_401(c.get("/api/yo", headers=con_token(token)))


def test_firma_es256_de_otra_clave_401(cliente, monkeypatch):
    jwks_falso(monkeypatch, CLAVE_EC.public_key())
    otra = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(claims(), otra, algorithm="ES256", headers={"kid": "kid-1"})
    assert_401(cliente.get("/api/yo", headers=con_token(token)))


# ---------- Perfil y roles ----------


def test_token_valido_sin_perfil_403(cliente):
    r = cliente.get("/api/yo", headers=con_token(token_hs(ID_SIN_PERFIL)))
    assert r.status_code == 403
    assert r.json() == {"detail": "Perfil no encontrado. Contacta al docente o administrador."}


SOLO_DOCENTE = requiere_rol("docente")
SOLO_ESTUDIANTE = requiere_rol("estudiante")
SOLO_ADMIN = requiere_rol("admin")


@pytest.fixture
def cliente_roles(sesion_compartida) -> TestClient:
    """App de prueba con rutas protegidas por rol (no toca main.py)."""
    router = APIRouter()

    @router.get("/solo-docente")
    def solo_docente(perfil: Annotated[Perfil, Depends(SOLO_DOCENTE)]) -> dict[str, str]:
        return {"rol": perfil.rol}

    @router.get("/solo-estudiante")
    def solo_estudiante(perfil: Annotated[Perfil, Depends(SOLO_ESTUDIANTE)]) -> dict[str, str]:
        return {"rol": perfil.rol}

    @router.get("/solo-admin")
    def solo_admin(perfil: Annotated[Perfil, Depends(SOLO_ADMIN)]) -> dict[str, str]:
        return {"rol": perfil.rol}

    app = FastAPI()
    app.include_router(router)
    return preparar(app, sesion_compartida, ajustes())


@pytest.mark.parametrize(
    ("ruta", "usuario", "esperado"),
    [
        ("/solo-docente", ID_ESTUDIANTE, 403),
        ("/solo-docente", ID_DOCENTE, 200),
        ("/solo-docente", ID_ADMIN, 200),
        ("/solo-estudiante", ID_ESTUDIANTE, 200),
        ("/solo-estudiante", ID_DOCENTE, 403),
        ("/solo-admin", ID_DOCENTE, 403),
        ("/solo-admin", ID_ADMIN, 200),
    ],
)
def test_requiere_rol(cliente_roles, ruta, usuario, esperado):
    r = cliente_roles.get(ruta, headers=con_token(token_hs(usuario)))
    assert r.status_code == esperado
    if esperado == 403:
        assert r.json() == {"detail": "No tienes permisos para esta acción"}


def test_requiere_rol_sin_token_401(cliente_roles):
    assert_401(cliente_roles.get("/solo-docente"))


def test_requiere_rol_rechaza_roles_desconocidos():
    with pytest.raises(ValueError):
        requiere_rol("superusuario")
    with pytest.raises(ValueError):
        requiere_rol()


# ---------- OpenAPI y CORS ----------


def test_openapi_documenta_seguridad_bearer(cliente):
    esquema = cliente.get("/openapi.json").json()
    assert esquema["paths"]["/api/yo"]["get"]["security"] == [{"HTTPBearer": []}]
    assert esquema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


@pytest.mark.parametrize("origen", ["http://localhost:3000", "https://mi-front.vercel.app"])
def test_cors_origen_permitido(sesion_compartida, origen):
    s = ajustes(frontend_url="https://mi-front.vercel.app/")
    c = preparar(crear_app(s), sesion_compartida, s)
    r = c.get("/api/salud", headers={"Origin": origen})
    assert r.headers.get("access-control-allow-origin") == origen
    pre = c.options(
        "/api/yo",
        headers={"Origin": origen, "Access-Control-Request-Method": "GET",
                 "Access-Control-Request-Headers": "authorization"},
    )
    assert pre.status_code == 200


def test_cors_origen_no_permitido(sesion_compartida):
    s = ajustes(frontend_url="https://mi-front.vercel.app")
    c = preparar(crear_app(s), sesion_compartida, s)
    r = c.get("/api/salud", headers={"Origin": "https://malicioso.example"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_nunca_comodin(sesion_compartida):
    s = ajustes(frontend_url="*")
    c = preparar(crear_app(s), sesion_compartida, s)
    r = c.get("/api/salud", headers={"Origin": "https://malicioso.example"})
    assert "access-control-allow-origin" not in r.headers


def test_tests_no_leen_env_real(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("SUPABASE_JWT_SECRET=no-deberia-leerse\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    assert Settings().supabase_jwt_secret == ""
