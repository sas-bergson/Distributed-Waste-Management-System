"""Zero-Trust token check (ADR-0001): this service verifies every access token itself.

RS256 only, fixed issuer and audience, 30 s clock tolerance. The public key comes from the
Auth service's JWKS endpoint (cached, refetched on an unknown `kid`) or, in development and
tests, from a PEM in AUTH_PUBLIC_KEY.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header

from app.config import get_settings
from app.problems import ProblemError, unauthorized
from app.schemas import Role

ALGORITHMS = ["RS256"]  # never accept "none" or HS256 (key-confusion attacks)


@dataclass(frozen=True)
class Principal:
    """Who is calling, from the token's claims."""

    sub: str
    role: Role
    tenant_id: str

    @property
    def sees_all_districts(self) -> bool:
        return self.role is Role.ADMIN


class TokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        leeway_seconds: int,
        public_key_pem: str | None = None,
        jwks_url: str | None = None,
        jwks_cache_seconds: int = 3600,
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._leeway = leeway_seconds
        # Env vars often carry PEMs on one line with literal "\n"
        self._public_key = public_key_pem.replace("\\n", "\n") if public_key_pem else None
        self._jwks = (
            jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=jwks_cache_seconds)
            if jwks_url and not self._public_key
            else None
        )

    def _signing_key(self, token: str) -> Any:
        if self._public_key:
            return self._public_key
        if self._jwks:
            # PyJWKClient refetches the key set when the token's `kid` is unknown (key rotation)
            return self._jwks.get_signing_key_from_jwt(token).key
        raise ProblemError(
            503,
            "auth-not-configured",
            "Token verification is not configured",
            "Set AUTH_JWKS_URL or AUTH_PUBLIC_KEY.",
        )

    def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._signing_key(token),
                algorithms=ALGORITHMS,
                issuer=self._issuer,
                audience=self._audience,
                leeway=self._leeway,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise unauthorized("Token expired") from None
        except (jwt.PyJWKClientError, jwt.InvalidTokenError) as exc:
            raise unauthorized(f"Invalid token: {exc}") from None

        try:
            role = Role(claims.get("role"))
        except ValueError:
            raise unauthorized("Invalid token: unknown role") from None
        sub, tenant_id = claims.get("sub"), claims.get("tenant_id")
        if not isinstance(sub, str) or not sub:
            raise unauthorized("Invalid token: missing sub")
        if not isinstance(tenant_id, str) or not tenant_id:
            raise unauthorized("Invalid token: missing tenant_id")
        return Principal(sub=sub, role=role, tenant_id=tenant_id)


@lru_cache
def get_verifier() -> TokenVerifier:
    settings = get_settings()
    return TokenVerifier(
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        leeway_seconds=settings.jwt_leeway_seconds,
        public_key_pem=settings.auth_public_key,
        jwks_url=settings.auth_jwks_url,
        jwks_cache_seconds=settings.jwks_cache_seconds,
    )


def get_principal(
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise unauthorized("Send Authorization: Bearer <access token>")
    return verifier.verify(token.strip())


CurrentUser = Annotated[Principal, Depends(get_principal)]
