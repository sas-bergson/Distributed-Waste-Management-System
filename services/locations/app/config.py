from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables (names are case-insensitive)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Set by docker-compose (Feature 1)
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/dwms"
    # .env.example: services own a schema each and never query each other's
    db_schema: str = "locations"

    # Token verification, ADR-0001. Set AUTH_JWKS_URL in the cluster,
    # AUTH_PUBLIC_KEY (PEM) for local development and tests.
    auth_jwks_url: str | None = None
    auth_public_key: str | None = None
    jwks_cache_seconds: int = 3600
    jwt_issuer: str = "dwms-auth-service"
    jwt_audience: str = "dwms-microservices"
    jwt_leeway_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
