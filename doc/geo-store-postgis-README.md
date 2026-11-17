# Geo Store (PostGIS)

Geospatial persistence layer of the Distributed Waste Management System (DWMS).

| | |
|---|---|
| **Component** | Geo Store (PostgreSQL + PostGIS) and its data-access layer |
| **Owning service** | `locations` (writes); `map` (read-only consumer) |
| **Objectives** | 1 - Collect waste-location information (primary); 2 - Color-coded map of waste amount and road condition |
| **Status** | Draft v0.1 - proposed design, pending review |
| **Audience** | Back-end, map, real-time and front-end contributors; reviewers of spatial and database changes |

> **How to read this document.** Statements marked **(prov.)** are provisional values or proposals, not measurements or agreed decisions. Anything under "Open decisions" (Section 15) must be settled by an ADR before implementation. Names of tables, endpoints and states must be aligned with the functional requirements and OpenAPI specifications in `docs/`.

---

## Table of contents

1. [Purpose and scope](#1-purpose-and-scope)
2. [Design principles](#2-design-principles)
3. [Architecture and boundaries](#3-architecture-and-boundaries)
4. [Data model](#4-data-model)
5. [Waste-location status lifecycle](#5-waste-location-status-lifecycle)
6. [Spatial design decisions](#6-spatial-design-decisions)
7. [Query catalogue](#7-query-catalogue)
8. [Service interface](#8-service-interface)
9. [Migrations](#9-migrations)
10. [Local development](#10-local-development)
11. [Testing strategy](#11-testing-strategy)
12. [Performance](#12-performance)
13. [Security and privacy](#13-security-and-privacy)
14. [Operations](#14-operations)
15. [Open decisions](#15-open-decisions)
16. [Contribution checklist](#16-contribution-checklist)

---

## 1. Purpose and scope

The Geo Store is the single source of truth for **where waste is, how much there is, what condition the road is in, and what has happened to each location over time**. Every other component (reporter app, dashboard, map service, SPF service, real-time service) reads or changes this data through the `locations` service. No client talks to the database directly.

### In scope

- Storing waste locations as geographic points, with the current waste amount and road condition.
- Storing every report (observation) made by a citizen or field agent, with photo references.
- Storing the status history of each location, including reopening after collection.
- Spatial queries: bounding box, nearest locations, duplicate detection, aggregation for low zoom levels.
- Idempotent ingestion of reports created offline and synchronised later.
- Publishing change events so the real-time service can update clients.

### Out of scope

- User identity, phone numbers, Google accounts and credentials (identity concern; the Geo Store holds only a pseudonymous user id).
- Photo binaries (stored in object storage; the Geo Store holds keys only).
- SPF request lifecycle details (owned by the `requests` service; the Geo Store only records the location status that results from it).
- Map styling and colors (owned by `palette.json` and the map service; the Geo Store stores bucket **codes**, never colors).

---

## 2. Design principles

1. **One writer, many readers.** Only the `locations` service writes. Other services use read-only database roles or the service API.
2. **Contract first.** Any change to a request, response or event shape is made in `docs/api/` before or with the code.
3. **Data, not presentation.** The database stores codes (`amount_bucket`, `road_condition`). Colors, labels and legends live in `palette.json` and the front ends. No hard-coded hex values anywhere.
4. **Append-only history.** Reports and status changes are never edited or deleted in normal operation. Current values on a location are derived from them.
5. **Idempotent by default.** A report carries a client-generated id, so retries and offline synchronisation can never create duplicates.
6. **Indexed or it does not ship.** Every spatial query used in production has a GiST-backed plan, verified with `EXPLAIN ANALYZE` in the pull request.
7. **Reversible migrations.** Every Alembic migration has a working downgrade.

---

## 3. Architecture and boundaries

```mermaid
flowchart LR
    R[Reporter app] --> G[gateway]
    D[Dashboard] --> G
    G --> L[locations service]
    L --> P[(PostgreSQL + PostGIS)]
    P --> M[map service - read only]
    L --> O[outbox events]
    O --> RT[realtime service]
    L --> S3[(Object storage - photos)]
    RQ[requests service - SPF] --> L
```

| Boundary | Rule |
|---|---|
| `gateway` -> `locations` | HTTP, contract in `docs/api/`. Authentication handled at the gateway. |
| `locations` -> database | The only service with write access. Uses its own database role. |
| `map` -> database | Read-only role, restricted to approved views and tables. |
| `locations` -> `realtime` | Transactional outbox. An event is written in the same transaction as the change, then published asynchronously. |
| `requests` -> `locations` | Calls the `locations` API to change a location status. Never writes SQL to the Geo Store. |

---

## 4. Data model

### 4.1 Entity overview

```mermaid
erDiagram
    ref_waste_amount_bucket ||--o{ waste_locations : classifies
    ref_road_condition ||--o{ waste_locations : classifies
    waste_locations ||--o{ location_reports : has
    waste_locations ||--o{ location_status_history : has
    waste_locations {
        uuid id PK
        geography geom
        text amount_bucket
        text road_condition
        text status
        int reopen_count
        int version
    }
    location_reports {
        uuid id PK
        uuid location_id FK
        uuid client_request_id UK
        text amount_bucket
        text road_condition
        text_array photo_keys
    }
    location_status_history {
        bigint id PK
        uuid location_id FK
        text from_status
        text to_status
    }
```

| Table | Purpose |
|---|---|
| `ref_waste_amount_bucket` | Lookup of waste-amount buckets (code, label, sort order). Values must match the buckets defined in the project README. |
| `ref_road_condition` | Lookup of road conditions. Values must match the project README. |
| `waste_locations` | One row per physical waste location. Holds the point and the **current** amount, road condition and status. |
| `location_reports` | Append-only observations. The first report creates the location; later reports update its current values. |
| `location_status_history` | Append-only log of every status transition, with who and when. |
| `outbox_events` | Events waiting to be published to the real-time service. |

### 4.2 Schema (reference DDL)

This is the reference design. The authoritative schema is the Alembic migration history.

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE ref_waste_amount_bucket (
    code        text     PRIMARY KEY,
    label       text     NOT NULL,
    sort_order  smallint NOT NULL UNIQUE
);

CREATE TABLE ref_road_condition (
    code        text     PRIMARY KEY,
    label       text     NOT NULL,
    sort_order  smallint NOT NULL UNIQUE
);

CREATE TABLE waste_locations (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    geom               geography(Point, 4326) NOT NULL,
    accuracy_m         real CHECK (accuracy_m IS NULL OR accuracy_m >= 0),
    amount_bucket      text NOT NULL REFERENCES ref_waste_amount_bucket (code),
    road_condition     text REFERENCES ref_road_condition (code),
    status             text NOT NULL DEFAULT 'reported'
                       CHECK (status IN ('reported', 'spf_requested',
                                         'collected', 'closed', 'reopened')),
    reopen_count       integer NOT NULL DEFAULT 0 CHECK (reopen_count >= 0),
    first_reported_by  uuid NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    version            integer NOT NULL DEFAULT 1
);

CREATE TABLE location_reports (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id        uuid NOT NULL REFERENCES waste_locations (id) ON DELETE RESTRICT,
    client_request_id  uuid NOT NULL UNIQUE,
    reported_by        uuid NOT NULL,
    amount_bucket      text REFERENCES ref_waste_amount_bucket (code),
    road_condition     text REFERENCES ref_road_condition (code),
    photo_keys         text[] NOT NULL DEFAULT '{}',
    reported_at        timestamptz NOT NULL,              -- device time
    received_at        timestamptz NOT NULL DEFAULT now(), -- server time
    CHECK (amount_bucket IS NOT NULL OR road_condition IS NOT NULL)
);

CREATE TABLE location_status_history (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id  uuid NOT NULL REFERENCES waste_locations (id) ON DELETE RESTRICT,
    from_status  text,
    to_status    text NOT NULL,
    changed_by   uuid NOT NULL,
    changed_at   timestamptz NOT NULL DEFAULT now(),
    note         text
);

CREATE TABLE outbox_events (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aggregate_id  uuid  NOT NULL,
    event_type    text  NOT NULL,
    payload       jsonb NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    published_at  timestamptz
);
```

### 4.3 Indexes

```sql
-- Spatial: all map and proximity queries
CREATE INDEX waste_locations_geom_gist
    ON waste_locations USING gist (geom);

-- Spatial, open locations only (the default map view); optional, measure first
CREATE INDEX waste_locations_geom_open_gist
    ON waste_locations USING gist (geom)
    WHERE status <> 'closed';

-- Filtering by status
CREATE INDEX waste_locations_open_status_idx
    ON waste_locations (status) WHERE status <> 'closed';

-- History and reports per location, newest first
CREATE INDEX location_reports_location_idx
    ON location_reports (location_id, received_at DESC);
CREATE INDEX location_status_history_location_idx
    ON location_status_history (location_id, changed_at DESC);

-- Outbox publisher
CREATE INDEX outbox_unpublished_idx
    ON outbox_events (id) WHERE published_at IS NULL;
```

`client_request_id` already has a unique index from its `UNIQUE` constraint, which is what makes ingestion idempotent.

### 4.4 Why the current values are stored on the location

The map needs one amount and one road condition per point, quickly. Computing them from the report history on every request would be slow and complex. The `locations` service therefore updates `amount_bucket`, `road_condition` and `status` in the same transaction that inserts a report or a history row. The history tables remain the audit trail.

---

## 5. Waste-location status lifecycle

States and transitions below are **(prov.)** and must be aligned with the state diagram in `docs/requirements/` (including confirmation after collection and reopening after collection).

```mermaid
stateDiagram-v2
    [*] --> reported
    reported --> spf_requested : SPF requested
    spf_requested --> collected : collection done
    collected --> closed : reporter confirms clean
    collected --> reopened : waste still present
    reopened --> spf_requested : SPF requested again
    reported --> closed : cancelled or duplicate
    closed --> [*]
```

Rules:

- Transitions are validated in the service layer. The database enforces the **set** of allowed values with a `CHECK` constraint.
- Every transition writes one row to `location_status_history` and increments `version`, in one transaction.
- `reopen_count` increases each time a location enters `reopened`.
- A `closed` location is not deleted. A new report at the same place within the duplicate radius (Section 7.3) is treated as a reopening, not a new location.

---

## 6. Spatial design decisions

| Topic | Decision (prov.) | Reason |
|---|---|---|
| Coordinate system | SRID **4326** (WGS 84, longitude/latitude) | What GPS devices and web maps deliver. |
| Column type | `geography(Point, 4326)` | Distances in metres and `ST_DWithin` use the GiST index directly, with no manual projection. |
| Axis order | **Longitude first**, then latitude, everywhere in SQL | `ST_MakePoint(lon, lat)`. Swapped axes are a classic and silent bug. |
| Index | GiST on `geom` | Supports bounding box, distance and nearest-neighbour. |
| Geometry for processing | Cast with `geom::geometry` only for functions that need it (grid aggregation, vector tiles) | Keeps the stored type simple and the common queries indexed. |
| Precision | Store full device precision; expose rounded coordinates where privacy requires | See Section 13. |

The choice of `geography` over `geometry` is recorded as an open decision (Section 15) because it affects every query, and should be confirmed by an ADR.

---

## 7. Query catalogue

Parameters are written as `:name`. Always use bound parameters, never string concatenation.

### 7.1 Insert a point

```sql
INSERT INTO waste_locations (geom, accuracy_m, amount_bucket, first_reported_by)
VALUES (
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
    :accuracy_m, :amount_bucket, :user_id
)
RETURNING id;
```

### 7.2 Locations inside the visible map area (bounding box)

```sql
SELECT l.id,
       ST_X(l.geom::geometry) AS lon,
       ST_Y(l.geom::geometry) AS lat,
       l.amount_bucket,
       l.road_condition,
       l.status
FROM   waste_locations l
WHERE  l.geom && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)::geography
  AND  l.status <> 'closed'
LIMIT  :limit;
```

### 7.3 Duplicate detection before creating a location

```sql
SELECT id
FROM   waste_locations
WHERE  ST_DWithin(
           geom,
           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
           :radius_m                       -- (prov.) 15 metres
       )
ORDER  BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
LIMIT  1;
```

If a row is returned, the report is attached to that location instead of creating a new one.

### 7.4 Nearest locations to a point

```sql
SELECT id,
       ST_Distance(geom, ref.p) AS distance_m
FROM   waste_locations,
       (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS p) AS ref
WHERE  status <> 'closed'
ORDER  BY geom <-> ref.p
LIMIT  :n;
```

### 7.5 Aggregation for low zoom (clustering)

At low zoom, return one cell per grid square instead of every point. The cell shows a count and the **worst** amount bucket in the cell, so the front end can colour it from the palette.

```sql
SELECT ST_AsGeoJSON(ST_SnapToGrid(l.geom::geometry, :cell_deg))::json AS cell,
       count(*)                                                       AS n,
       max(b.sort_order)                                              AS worst_amount_rank
FROM   waste_locations l
JOIN   ref_waste_amount_bucket b ON b.code = l.amount_bucket
WHERE  l.geom && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)::geography
  AND  l.status <> 'closed'
GROUP  BY ST_SnapToGrid(l.geom::geometry, :cell_deg);
```

The grid size `:cell_deg` is derived from the zoom level by the map service. Server-side vector tiles (`ST_AsMVT`) are an alternative, listed in Section 15.

### 7.6 Status history of a location

```sql
SELECT from_status, to_status, changed_by, changed_at, note
FROM   location_status_history
WHERE  location_id = :id
ORDER  BY changed_at DESC;
```

---

## 8. Service interface

The Geo Store is reached through the `locations` service. The endpoints below are **(prov.)** and illustrate the intended contract. The authoritative definition is the OpenAPI specification in `docs/api/`.

| Method and path | Purpose |
|---|---|
| `POST /locations/reports` | Submit a report. Creates a location or attaches to an existing one. Idempotent on `client_request_id`. |
| `GET /locations?bbox=minLon,minLat,maxLon,maxLat` | Locations in the visible map area. |
| `GET /locations/clusters?bbox=...&zoom=...` | Aggregated cells for low zoom. |
| `GET /locations/nearby?lon=...&lat=...&limit=...` | Nearest open locations. |
| `GET /locations/{id}` | One location with its current values. |
| `GET /locations/{id}/history` | Status history. |
| `POST /locations/{id}/status` | Request a status transition (validated server-side). |

Conventions:

- **Idempotency:** repeating `POST /locations/reports` with the same `client_request_id` returns the original result and creates nothing new.
- **Optimistic concurrency:** status changes send the expected `version`. A mismatch returns a conflict response.
- **Errors:** invalid coordinates, unknown bucket codes and illegal transitions return client errors with a stable error code, never a database message.

### Events (outbox)

| Event type | When |
|---|---|
| `location.created` | A new location is created. |
| `location.updated` | Current amount or road condition changes. |
| `location.status_changed` | A status transition is recorded. |

Payloads are defined in `docs/api/`. Events carry ids and current values, never personal data.

---

## 9. Migrations

- Tool: **Alembic**. One concern per migration.
- Every migration is **reversible**: `upgrade()` and `downgrade()` both work, and CI runs upgrade, downgrade, upgrade.
- Create the PostGIS extension in the first migration (`CREATE EXTENSION IF NOT EXISTS postgis`).
- Prefer lookup tables and `CHECK` constraints over native PostgreSQL enum types: they are easier to change in a reversible migration.
- Never edit a migration that has been merged. Add a new one.
- Large index builds on populated tables use `CREATE INDEX CONCURRENTLY` (in a migration that runs outside a transaction).
- Seed data for the reference tables is a migration, and its values must match the project README.

Minimal pattern:

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        CREATE TABLE waste_locations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            geom geography(Point, 4326) NOT NULL
            -- remaining columns as in Section 4.2
        )
        """
    )
    op.execute(
        "CREATE INDEX waste_locations_geom_gist ON waste_locations USING gist (geom)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS waste_locations_geom_gist")
    op.execute("DROP TABLE IF EXISTS waste_locations")
```

---

## 10. Local development

### Prerequisites

- Docker, `uv` and `pre-commit` (see the project README).

### Start a local PostGIS database

```yaml
# docker-compose.yml (excerpt)
services:
  db:
    image: postgis/postgis:16-3.4     # pin an exact tag and verify it in the registry
    environment:
      POSTGRES_DB: dwms
      POSTGRES_USER: dwms
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}   # from your local .env, never committed
    ports:
      - "5432:5432"
    volumes:
      - dwms_pgdata:/var/lib/postgresql/data
volumes:
  dwms_pgdata:
```

```bash
docker compose up -d db
export DATABASE_URL="postgresql://dwms:${POSTGRES_PASSWORD}@localhost:5432/dwms"
uv run alembic upgrade head
```

Check that PostGIS is active:

```sql
SELECT postgis_full_version();
```

Rules: `.env` files and credentials are never committed. Use only synthetic data in development, never real citizen data.

---

## 11. Testing strategy

| Level | What is verified | Tooling |
|---|---|---|
| Migration | `upgrade`, `downgrade`, `upgrade` all succeed on an empty database | `pytest` against a real PostGIS container |
| Repository | Inserts, duplicate detection, bounding box, nearest, aggregation return correct rows | `pytest` with seeded synthetic points |
| Idempotency | Same `client_request_id` twice creates one report | `pytest` |
| Transitions | Every allowed transition succeeds, every other is rejected, history rows are written | `pytest` |
| Plan checks | Production queries use the GiST index (`EXPLAIN` shows an index scan) | `pytest` on a seeded table large enough for the planner to prefer the index |
| Contract | Responses match `docs/api/` | Contract test in CI |

Test data must include edge cases: points on the antimeridian and near poles (valid but unusual), swapped latitude/longitude, coordinates outside the pilot area, null accuracy, and identical coordinates from different users.

Run before every pull request:

```bash
uv run pytest -q
pre-commit run --all-files
```

---

## 12. Performance

All figures below are **(prov.)** targets to be confirmed by measurement, not guarantees.

| Query | Target at 1 million locations (prov.) |
|---|---|
| Bounding box, up to 500 rows | p95 under 100 ms |
| Nearest 20 locations | p95 under 50 ms |
| Duplicate check on insert | p95 under 30 ms |
| Grid aggregation, city-wide | p95 under 300 ms |

Practices:

- Review `EXPLAIN (ANALYZE, BUFFERS)` for every new spatial query and paste it in the pull request.
- Always limit result sizes. A map request never returns an unbounded set.
- Run `ANALYZE` after bulk loads. Keep autovacuum enabled and monitor table bloat.
- If the open-locations map is the dominant query, measure the partial GiST index in Section 4.3 against the full index before keeping both.
- Plan for growth: partition `location_reports` and `location_status_history` by time only after measurement shows a need.

---

## 13. Security and privacy

- **No personal data in the Geo Store.** Users appear only as pseudonymous UUIDs. Phone numbers and Google identifiers stay in the identity component.
- **Location is sensitive.** Precise coordinates can reveal where a person was. Access is limited by role, and public views may round coordinates (precision to be decided).
- **Least privilege.** Separate database roles: `locations` (read and write on its tables), `map` (read-only on approved views), migration role (schema changes only), no application role is a superuser.
- **Parameterised queries only.** No SQL assembled from user input.
- **Input validation at the boundary:** valid longitude and latitude ranges, known bucket codes, accuracy not negative, photo keys match the expected pattern, report count and size limits.
- **Transport and storage:** TLS to the database in every non-local environment; encrypted backups.
- **Secrets:** read from environment or a secrets manager. Never committed.
- **Retention:** a retention and anonymisation rule for old reports must be agreed (Section 15).

---

## 14. Operations

- **Backups:** scheduled base backups plus write-ahead log archiving for point-in-time recovery. Restore is rehearsed, not assumed.
- **Monitoring:** slow queries (`pg_stat_statements`), connection count, replication lag if replicas are used, table and index size, outbox backlog (rows where `published_at IS NULL`).
- **Outbox publisher:** polls unpublished events in order, publishes, then sets `published_at`. It must tolerate restarts and deliver at least once; consumers must be idempotent.
- **PostGIS upgrades:** upgrade the PostGIS package, then run `ALTER EXTENSION postgis UPDATE` (or `SELECT postgis_extensions_upgrade()`), after testing on a copy of production data.
- **Index maintenance:** `REINDEX` when bloat is measured, not on a calendar.
- **Disaster recovery targets:** recovery point and recovery time objectives to be defined with the team **(prov.)**.

---

## 15. Open decisions

Each item needs a short ADR before implementation.

| # | Decision | Options | Impact |
|---|---|---|---|
| 1 | Stored column type | `geography` (proposed) or `geometry` with projection | Every spatial query and index |
| 2 | Status list and transitions | Align with the requirements state diagram | Service logic, history, API, events |
| 3 | Duplicate radius | 15 m proposed (prov.); may vary with GPS accuracy | Data quality, reopening behaviour |
| 4 | Clustering approach | Server-side grid (proposed), `ST_ClusterDBSCAN`, or vector tiles with `ST_AsMVT` | Map service, performance |
| 5 | Who may change status | Reporter, field agent, operator roles; links to the SPF create/cancel question | Permissions in several services |
| 6 | Retention and anonymisation | Period and method for old reports | Privacy, storage |
| 7 | Event delivery | Polling outbox (proposed) or logical replication / `LISTEN/NOTIFY` | Real-time latency and complexity |
| 8 | Service-area limit | Reject points outside the pilot region, or accept all | Data quality, abuse prevention |
| 9 | Editing after submission | Whether a reporter can correct a location or amount | History model, API |

---

## 16. Contribution checklist

For any pull request touching the Geo Store:

- Declare **Objective 1** and, if the map is affected, **Objective 2**. Services touched: `locations`, and `map` if applicable.
- Fill in the **Spatial / database changes** section of the pull request template.
- Include a **reversible Alembic migration**.
- Show that each new spatial query **uses a GiST index**, with `EXPLAIN ANALYZE` output attached (redact if needed).
- Update `docs/api/` if any request, response or event changed, and this document if the model changed.
- Add tests at the right level (Section 11).
- No secrets, no real citizen data, no hard-coded palette values.
- Disclose any AI assistance and state how you verified the result.
- Keep the pull request to one concern and under about 400 changed lines.
