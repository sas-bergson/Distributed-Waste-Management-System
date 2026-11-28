"""Sign development access tokens until the Auth service (Feature 12) exists.

    python scripts/dev_token.py --role citizen --tenant district-douala-01

First run creates an RSA key pair in .dev-keys/ (gitignored). Start the service with the
public key so it accepts these tokens:

    AUTH_PUBLIC_KEY="$(cat .dev-keys/public.pem)" uvicorn app.main:app --port 8001

Tokens follow ADR-0001: RS256, iss/aud, sub, role, tenant_id, iat, exp, jti.
"""

import argparse
import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEY_DIR = Path(__file__).resolve().parent.parent / ".dev-keys"
ROLES = ["citizen", "field_agent", "supervisor", "admin"]


def load_or_create_private_key() -> bytes:
    private_path = KEY_DIR / "private.pem"
    if private_path.exists():
        return private_path.read_bytes()
    KEY_DIR.mkdir(exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    private_path.write_bytes(private_pem)
    (KEY_DIR / "public.pem").write_bytes(public_pem)
    print(f"Created a dev key pair in {KEY_DIR}")
    return private_pem


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--role", choices=ROLES, default="citizen")
    parser.add_argument("--tenant", default="district-douala-01")
    parser.add_argument("--sub", default=None, help="user id (default: a new UUID)")
    parser.add_argument("--minutes", type=int, default=15, help="lifetime (ADR-0001: 15)")
    args = parser.parse_args()

    now = int(time.time())
    claims = {
        "iss": "dwms-auth-service",
        "aud": "dwms-microservices",
        "sub": args.sub or str(uuid.uuid4()),
        "role": args.role,
        "tenant_id": args.tenant,
        "iat": now,
        "exp": now + args.minutes * 60,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        claims, load_or_create_private_key(), algorithm="RS256", headers={"kid": "dev"}
    )
    print(token)


if __name__ == "__main__":
    main()
