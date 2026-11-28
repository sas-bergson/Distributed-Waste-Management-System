# Location Reporting Service (`services/locations`)

Objective 1 — collect waste-location information. **Feature 18 (Waste report API), IMP:**
the user-facing endpoints. Claim: Discussion #51 · PR #13 · Contract: [`docs/api/locations.yaml`](../../docs/api/locations.yaml).

| Endpoint | What it does |
|---|---|
| `GET /healthz` (also `/health`) | Service + database check, no token |
| `POST /reports` | Submit a report (position, amount bucket, waste type, …). Reporter comes from the token |
| `GET /reports` | List newest first: `bbox`, `amount_bucket`, `waste_type`, `status`, `updated_since`, cursor paging |
| `GET /reports/{id}` | One report, with its `ETag` |
| `PATCH /reports/{id}` | Change amount, type, description or status. Needs `If-Match` |

The IoT/device endpoint is the second Feature 18 implementer's part.

## How it works

- **Tokens (ADR-0001, agreed with Feature 12 in #17).** The service checks every token itself
  (Zero-Trust): `RS256` only, `iss = dwms-auth-service`, `aud = dwms-microservices`, `exp`/`iat`
  with 30 s clock tolerance, claims `sub`, `role`, `tenant_id`. Public key from `AUTH_JWKS_URL`
  (cached 1 h, refetched on an unknown `kid`) or `AUTH_PUBLIC_KEY` (PEM) for development.
- **District isolation.** Users only see and change their own district's reports (`tenant_id`);
  another district's report answers `404`. `admin` sees all districts.
- **No lost updates.** Each report has a `version` (sent as `ETag`). `PATCH` must send it back in
  `If-Match`; the database applies the change only if the version still matches
  (`UPDATE … WHERE version = n`), otherwise `412`. Two agents can't silently overwrite each other.
- **Who may change what.** `citizen`: only the description of their own report.
  `field_agent`, `supervisor`, `admin`: every field.
- **Storage.** PostGIS `POINT` (SRID 4326) in the `locations` schema, GiST index for map-area
  queries, timestamps from the database clock. Migration: `alembic/versions/0001_…`
  (Feature 21 owns the full schema and seed data and builds on this table).
- **Errors.** RFC 9457 Problem Details (`application/problem+json`) with per-field messages.

## Run it

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows; use .venv/bin/ on Linux/macOS
```

Tokens until the Auth service exists (creates a key pair in `.dev-keys/`, gitignored):

```bash
python scripts/dev_token.py --role field_agent --tenant district-douala-01
```

Start the service against a PostGIS database:

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dwms
export AUTH_PUBLIC_KEY="$(cat .dev-keys/public.pem)"
alembic upgrade head
uvicorn app.main:app --port 8001
```

Open http://localhost:8001/docs, click **Authorize**, paste the token.

In Docker Compose (Feature 1) the service is built from this folder's `Dockerfile`, listens on
`8001` and runs `alembic upgrade head && uvicorn app.main:app`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/dwms` | Set by docker-compose |
| `DB_SCHEMA` | `locations` | This service's schema |
| `AUTH_JWKS_URL` | — | Auth service JWKS, e.g. `http://gateway:8000/.well-known/jwks.json` |
| `AUTH_PUBLIC_KEY` | — | PEM public key (dev/tests), used instead of JWKS when set |
| `JWT_ISSUER` / `JWT_AUDIENCE` | `dwms-auth-service` / `dwms-microservices` | ADR-0001 |
| `JWT_LEEWAY_SECONDS` | `30` | Clock tolerance |

## Checks

```bash
pytest -q            # 55 tests: auth rules, endpoints, isolation, paging, concurrency, SQL
ruff check . && ruff format --check .
mypy app             # strict
alembic upgrade head --sql   # migration SQL without a database
```

The tests use an in-memory repository with the same rules as the PostGIS one, plus checks of
the SQL the PostGIS repository generates. They have not yet run against a live PostGIS database.
