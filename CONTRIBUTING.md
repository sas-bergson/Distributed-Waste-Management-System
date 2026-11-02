# Contributing to the Distributed Waste Management System (DWMS)

First off — thank you. This is a **capstone project built by students, for students**, and it is meant to be forked, extended, and argued with. Whether you are fixing a typo in the palette legend or reworking the SPF request lifecycle, this document tells you how we work.

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Be generous with review comments and stingy with assumptions.

---

## Table of Contents

- [Before You Start](#before-you-start)
- [Tech Stack in Detail](#tech-stack-in-detail)
  - [Language & Runtime Versions](#language--runtime-versions)
  - [Stack by Service](#stack-by-service)
  - [Data Stores](#data-stores)
  - [Mapping & Frontend](#mapping--frontend)
  - [Tooling & Quality Gates](#tooling--quality-gates)
  - [Infrastructure](#infrastructure)
- [Local Development Setup](#local-development-setup)
- [Objective Traceability](#objective-traceability)
- [Branching Strategy](#branching-strategy)
- [Commit Convention](#commit-convention)
- [Code Style by Language](#code-style-by-language)
- [Testing Requirements](#testing-requirements)
- [Working with the Map & Palette](#working-with-the-map--palette)
- [Working with the API Contract](#working-with-the-api-contract)
- [Pull Request Process](#pull-request-process)
- [Definition of Done](#definition-of-done)
- [Issue Reporting & Claiming Work](#issue-reporting--claiming-work)
- [Dependency & Secrets Policy](#dependency--secrets-policy)
- [Data Privacy Rules](#data-privacy-rules)
- [For Maintainers & Instructors](#for-maintainers--instructors)
- [Useful Commands](#useful-commands)

---

## Before You Start

1. Read the [README](README.md) — particularly **Project Objectives** and the **Map & Color Palette Specification**. Objectives are the scope contract; the palette is a specification, not a preference.
2. Check the [Discussions](https://github.com/<your-org>/distributed-waste-management/discussions) and open issues for existing work on your idea. Duplicate effort is the most common way capstone teams lose a week.
3. Set up your environment (below) and run `docker compose up` **before** you write any code. If the skeleton does not run on your machine, that is itself a bug — open an issue.

---

## Tech Stack in Detail

DWMS is deliberately **polyglot but tightly bounded**: Python for data‑ and geo‑heavy services, TypeScript/Node for I/O‑dense services and the frontend, and a spatial relational database at the centre. Do not introduce a new language or framework without an ADR (see [Architecture Decision Records](#working-with-the-map--palette)).

### Language & Runtime Versions

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | 3.11+ | Backend services, simulators, scripts |
| **Node.js** | 20 LTS+ | Gateway, real‑time hub, frontend build |
| **TypeScript** | 5.x | Required for all Node services and frontend |
| **PostgreSQL** | 16 | With **PostGIS 3.4+** |
| **Redis** | 7 | Pub/Sub backplane + caching |
| **Docker Engine** | 24+ | With Compose v2 (`docker compose`, not `docker-compose`) |
| **Kubernetes** | 1.28+ | Optional, for the scale milestone only |

> **Version policy:** pin versions in `pyproject.toml` / `package.json` and in the Dockerfiles. If your change requires a runtime upgrade, propose it in an ADR — a mid‑semester Node upgrade has broken more capstones than any algorithm bug.

### Stack by Service

Each service owns its dependencies. You should only need to install the toolchain for the service you are working on.

| Path | Language | Framework | Key Libraries | Purpose |
|------|----------|-----------|---------------|---------|
| `services/gateway/` | TypeScript | Fastify | `@fastify/jwt`, `@fastify/rate-limit`, `@fastify/cors` | Auth, rate limiting, request routing to internal services |
| `services/locations/` | Python | FastAPI | Pydantic v2, SQLAlchemy 2, **GeoAlchemy2**, Alembic | Waste‑location reporting and ingestion (**Obj. 1**) |
| `services/map/` | Python | FastAPI | GeoAlchemy2, `shapely`, `palette.json` loader | Viewport GeoJSON / tiles and palette application (**Obj. 2**) |
| `services/requests/` | Python | FastAPI | Pydantic v2, SQLAlchemy 2, `httpx` | SPF request lifecycle and dispatch (**Obj. 3**) |
| `services/realtime/` | TypeScript | Node + `ws` | `ioredis`, `socket.io` (if chosen) | WebSocket/SSE hub, Redis Pub/Sub fan‑out (**Obj. 3**) |
| `services/notifications/` | Python | FastAPI + worker | `arq` or Celery, `httpx` | Async email/SMS/push delivery (**Obj. 3**) |
| `simulator/iot_bins/` | Python | CLI | `paho-mqtt` | Smart‑bin telemetry simulation |
| `simulator/field_reports/` | Python | CLI | `requests`, `faker` | Scripted waste‑location report generation |
| `frontend/dashboard/` | TypeScript | React 18 + Vite | **MapLibre GL JS**, TanStack Query, Tailwind | Operations map, legend, SPF queue |
| `frontend/reporter/` | TypeScript | React 18 + Vite | TanStack Query, `react-hook-form` | Citizen / field‑agent reporting app |

> **Rule:** a service must not reach directly into another service's database. Cross‑service data flows go through HTTP or the event/real‑time channel. If you are tempted to add a foreign key across service schemas, open a Discussion first.

### Data Stores

| Store | Used for | Owned by |
|-------|----------|----------|
| **PostgreSQL + PostGIS** | Waste locations (geometry), road segments, SPF requests, audit trail | `locations`, `requests` (separate schemas) |
| **Redis** | Pub/Sub backplane for real‑time fan‑out, viewport query cache | `realtime`, `map` |
| **MQTT (Mosquitto)** | IoT bin telemetry ingestion | `locations` (subscriber) |

Spatial queries must use PostGIS functions (`ST_DWithin`, `ST_Intersects`, `ST_AsGeoJSON`) and **must** be backed by a GiST index. A viewport query without an index is a review blocker.

### Mapping & Frontend

- **MapLibre GL JS** is the mapping library (open‑source, no API key required — this matters for a student project).
- Map styling lives in `services/map/style/` and is **loaded from `palette.json`** — never hard‑code hex values in components.
- Base map tiles: use an openly licensed tile source, or a local tile server in `infrastructure/`. Do not commit API keys for commercial tile providers.
- The **legend is a required component**, not optional UI. Any PR touching map rendering must keep both dimensions (waste amount, road condition) legible.

### Tooling & Quality Gates

| Concern | Tool | Applies to |
|---------|------|------------|
| Python lint + format | **Ruff** (`ruff check`, `ruff format`) | All Python |
| Python types | **mypy** (strict for services) | All Python services |
| JS/TS lint + format | **ESLint** + **Prettier** | All TS/Node code |
| TS types | `tsc --noEmit` | Gateway, realtime, frontend |
| Python tests | **pytest** + `httpx.AsyncClient` | Services |
| JS/TS tests | **Vitest** | Gateway, realtime, frontend |
| End‑to‑end | **Playwright** | `tests/e2e/` |
| Load testing | **k6** | Scale milestone |
| Pre‑commit hooks | **pre-commit** | Everything (runs the above on staged files) |
| CI | **GitHub Actions** | Everything (see `.github/workflows/`) |

### Infrastructure

- **Docker Compose** for local development — this is the primary developer experience. `docker compose up` must work from a clean clone.
- **Kubernetes** manifests in `infrastructure/k8s/` for the scale milestone only. Do not require a cluster to develop a feature.
- **Terraform** in `infrastructure/terraform/` is optional and must never be applied against a real cloud account without instructor approval.
- Every new service must include: `Dockerfile`, health endpoint (`GET /healthz`), and a Compose service block with pinned image tags.

---

## Local Development Setup

### 1. Prerequisites

- Docker Engine 24+ with Compose v2
- Python 3.11+ with `uv` (preferred) or `venv` + `pip`
- Node.js 20 LTS+ with **pnpm** (do not mix package managers within a service)
- `pre-commit`

### 2. Bootstrap

```bash
git clone https://github.com/<your-org>/distributed-waste-management.git
cd distributed-waste-management
cp .env.example .env            # never commit .env
pre-commit install              # installs lint/format hooks
docker compose up --build       # gateway + PostGIS + Redis + MQTT + services
