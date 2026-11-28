import time
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import TokenVerifier, get_verifier
from app.main import create_app
from app.repository import get_repository
from tests.fakes import InMemoryReportRepository

TenantToken = Callable[..., str]


def _new_key_pair() -> tuple[bytes, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def keys() -> tuple[bytes, str]:
    """The Auth service's key pair, as far as these tests are concerned."""
    return _new_key_pair()


@pytest.fixture(scope="session")
def other_private_key() -> bytes:
    """A key the service does not trust."""
    return _new_key_pair()[0]


@pytest.fixture
def make_token(keys: tuple[bytes, str]) -> TenantToken:
    """An ADR-0001 access token; override any claim with keyword arguments."""

    def make(
        role: str = "citizen",
        tenant_id: str | None = "district-douala-01",
        sub: str | None = None,
        signing_key: bytes | None = None,
        algorithm: str = "RS256",
        drop: tuple[str, ...] = (),
        **overrides: Any,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": "dwms-auth-service",
            "aud": "dwms-microservices",
            "sub": str(uuid.uuid4()) if sub is None else sub,
            "role": role,
            "tenant_id": tenant_id,
            "iat": now,
            "exp": now + 900,
            "jti": str(uuid.uuid4()),
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None and k not in drop}
        return jwt.encode(claims, signing_key or keys[0], algorithm=algorithm)

    return make


@pytest.fixture
def repo() -> InMemoryReportRepository:
    return InMemoryReportRepository()


@pytest.fixture
async def client(
    keys: tuple[bytes, str], repo: InMemoryReportRepository
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    verifier = TokenVerifier(
        issuer="dwms-auth-service",
        audience="dwms-microservices",
        leeway_seconds=30,
        public_key_pem=keys[1],
    )
    app.dependency_overrides[get_verifier] = lambda: verifier
    app.dependency_overrides[get_repository] = lambda: repo
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://locations") as c:
        yield c


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
