"""ADR-0001 token rules, checked through a real endpoint."""

import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest

from tests.conftest import TenantToken, bearer

pytestmark = pytest.mark.anyio


async def _list(client: httpx.AsyncClient, token: str | None) -> httpx.Response:
    return await client.get("/reports", headers=bearer(token) if token else {})


async def test_valid_token_is_accepted(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    assert (await _list(client, make_token())).status_code == 200


async def test_missing_token_is_401_with_bearer_challenge(client: httpx.AsyncClient) -> None:
    response = await _list(client, None)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "someone-else"},
        {"aud": "another-audience"},
        {"exp": int(time.time()) - 120},  # expired beyond the 30 s tolerance
        {"tenant_id": None},
        {"role": "superuser"},
        {"drop": ("sub",)},
        {"sub": ""},
        {"drop": ("iat",)},
    ],
    ids=[
        "issuer",
        "audience",
        "expired",
        "no-tenant",
        "unknown-role",
        "no-sub",
        "empty-sub",
        "no-iat",
    ],
)
async def test_bad_claims_are_rejected(
    client: httpx.AsyncClient, make_token: TenantToken, overrides: dict[str, object]
) -> None:
    assert (await _list(client, make_token(**overrides))).status_code == 401


async def test_clock_skew_within_30_seconds_is_tolerated(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    token = make_token(exp=int(time.time()) - 10)
    assert (await _list(client, token)).status_code == 200


async def test_token_signed_with_untrusted_key_is_rejected(
    client: httpx.AsyncClient, make_token: TenantToken, other_private_key: bytes
) -> None:
    token = make_token(signing_key=other_private_key)
    assert (await _list(client, token)).status_code == 401


def _forge(algorithm: str, secret: bytes | None) -> str:
    """Hand-built token, since PyJWT itself refuses to create these attacks."""

    def b64(data: bytes) -> bytes:
        return base64.urlsafe_b64encode(data).rstrip(b"=")

    now = int(time.time())
    claims = {
        "iss": "dwms-auth-service",
        "aud": "dwms-microservices",
        "sub": "x",
        "role": "admin",
        "tenant_id": "t",
        "iat": now,
        "exp": now + 60,
    }
    signing_input = (
        b64(json.dumps({"alg": algorithm, "typ": "JWT"}).encode())
        + b"."
        + b64(json.dumps(claims).encode())
    )
    signature = b64(hmac.new(secret, signing_input, hashlib.sha256).digest()) if secret else b""
    return (signing_input + b"." + signature).decode()


async def test_hs256_token_using_the_public_key_as_secret_is_rejected(
    client: httpx.AsyncClient, keys: tuple[bytes, str]
) -> None:
    """Algorithm-confusion attack from ADR-0001: only RS256 is accepted."""
    forged = _forge("HS256", keys[1].encode())
    assert (await _list(client, forged)).status_code == 401


async def test_unsigned_token_is_rejected(client: httpx.AsyncClient) -> None:
    assert (await _list(client, _forge("none", None))).status_code == 401
