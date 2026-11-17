# Geo Store (PostGIS)

**Technical Design and Operations Guide**
Distributed Waste Management System (DWMS)

---

## Document control

| Field | Value |
|---|---|
| Document ID | DWMS-GEO-001 (assign according to the project's documentation convention) |
| Version | 0.2 |
| Status | Draft for technical review |
| Last updated | 16 November 2026 |
| Component | Geo Store: PostgreSQL with PostGIS, and its data-access layer |
| Owning service | `locations` (read/write); `map` (read-only consumer) |
| Project objectives | Objective 1 (primary): Collect waste-location information. Objective 2: Color-coded map of waste amount and road condition. |
| Owner | To be assigned (Geo Store squad lead) |
| Reviewers | Back-end, map, real-time and data squad leads; architecture group |
| Related documents | Project `README.md`, `CONTRIBUTING.md`, `docs/requirements/`, `docs/api/`, `docs/adr/`, `palette.json` |

### Version history

| Version | Date | Description |
|---|---|---|
| 0.1 | 16 November 2026 | Initial draft: purpose, data model, queries, operations. |
| 0.2 | 16 November 2026 | Added executive summary, requirements traceability, data integrity rules, availability and recovery targets, risk register, decision register, glossary. |

### Conventions used in this document

| Marker | Meaning |
|---|---|
| **(prov.)** | A provisional value or proposal. It is not a measurement and not an agreed decision. |
| **Confirmed** | Already stated in the project's contribution tooling or requirements. |
| **Proposed** | Recommended by this design and subject to review or an ADR. |

Table names, endpoints, states and numeric targets in this document must be aligned with the functional requirements in `docs/requirements/` and the OpenAPI specifications in `docs/api/` before implementation. Where this document and an approved ADR disagree, the ADR prevails.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Scope](#2-scope)
3. [Requirements traceability](#3-requirements-traceability)
4. [Design principles](#4-design-principles)
5. [Architecture and boundaries](#5-architecture-and-boundaries)
6. [Data model](#6-data-model)
7. [Waste-location status lifecycle](#7-waste-location-status-lifecycle)
8. [Spatial design decisions](#8-spatial-design-decisions)
9. [Query catalogue](#9-query-catalogue)
10. [Service interface and events](#10-service-interface-and-events)
11. [Data integrity and validation rules](#11-data-integrity-and-validation-rules)
12. [Migration policy](#12-migration-policy)
13. [Development environment](#13-development-environment)
14. [Testing strategy](#14-testing-strategy)
15. [Non-functional requirements](#15-non-functional-requirements)
16. [Operations](#16-operations)
17. [Risk register](#17-risk-register)
18. [Decision register](#18-decision-register)
19. [Contribution standards and definition of done](#19-contribution-standards-and-definition-of-done)
20. [Appendix A: Glossary](#appendix-a-glossary)

---

## 1. Executive summary

The Geo Store is the system of record for **where waste is, how much there is, what condition the road is in, and what has happened to each location over time**. It is implemented on PostgreSQL with the PostGIS extension and is accessed only through the `locations` service.

The design rests on four commitments:

1. **A single writer.** Only the `locations` service changes data. All other components read through the service API or restricted read-only database roles.
2. **Append-only history with a fast current view.** Every report and status change is recorded permanently. The current amount, road condition and status are kept on the location row so the map can be served quickly.
3. **Idempotent ingestion.** Every report carries a client-generated identifier. Offline synchronisation and network retries cannot create duplicates.
4. **Indexed, reversible and tested.** Every production spatial query has a GiST-backed plan verified with `EXPLAIN ANALYZE`. Every migration can be rolled back. Both are enforced in review and CI.

The Geo Store deliberately holds **no personal data and no presentation data**. Users appear only as pseudonymous identifiers, and the database stores classification codes, never colors.

---

## 2. Scope

### 2.1 In scope

- Storing waste locations as geographic points, with the current waste amount, road condition and status.
- Storing every report (observation) from a citizen or field agent, with references to photos.
- Storing the status history of each location, including reopening after collection.
- Spatial queries: visible-area (bounding box), nearest locations, duplicate detection, and aggregation for low zoom levels.
- Idempotent ingestion of reports created offline and synchronised later.
- Publishing change events so the real-time service can update connected clients.

### 2.2 Out of scope

| Item | Owner |
|---|---|
| User identity, phone numbers, Google accounts, credentials | Identity component |
| Photo files (the Geo Store stores object keys only) | Object storage |
| SPF request lifecycle and its own data | `requests` service |
| Map styling, colors, legends | `palette.json` and the front ends |
| Push notification delivery | `realtime` service |

---

## 3. Requirements traceability

This table links the Geo Store to the objectives and to the requirement areas of the Citizen / Field Agent application. Individual requirement identifiers (FR-RA-xx) should be added in the final column when this document is reviewed against `docs/requirements/`.

| Objective | Requirement area | Geo Store capability | Section | Requirement IDs |
|---|---|---|---|---|
| 1 | Waste-location reporting | Location and report storage, duplicate detection | 6, 9.3 | To be mapped |
| 1 | Road-condition reporting | Road condition on reports and current location view | 6 | To be mapped |
| 1 | Offline operation and synchronisation | Idempotent ingestion by `client_request_id`; device time versus server time | 6, 10 | To be mapped |
| 1 | Waste-location status as seen by the reporter | Status lifecycle, including reopening after collection | 7 | To be mapped |
| 2 | Map and visualisation | Visible-area queries and low-zoom aggregation | 9.2, 9.5 | To be mapped |
| 3 | SPF requests | Status transitions driven by the `requests` service | 5, 7 | To be mapped |
| 3 | Real-time updates and notifications | Transactional outbox and change events | 10.2 | To be mapped |

---

## 4. Design principles

| # | Principle | Practical consequence |
|---|---|---|
| 1 | One writer, many readers | Only `locations` writes. Other services use read-only roles or the API. |
| 2 | Contract first | Request, response and event shapes are changed in `docs/api/` before or with the code. |
| 3 | Data, not presentation | The database stores codes (`amount_bucket`, `road_condition`). Colors live in `palette.json`. No hard-coded hex values. |
| 4 | Append-only history | Reports and status changes are not edited or deleted in normal operation. |
| 5 | Idempotent by default | Client-generated identifiers make retries and offline sync safe. |
| 6 | Indexed or it does not ship | Spatial queries must show an index-backed plan in the pull request. |
| 7 | Reversible change | Every migration has a tested downgrade. |
| 8 | Privacy by design | No personal data in the Geo Store; coordinates are treated as sensitive. |

---

## 5. Architecture and boundaries

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
| `gateway` to `locations` | HTTP. Contract in `docs/api/`. Authentication is handled at the gateway. |
| `locations` to database | The only service with write access, using its own database role. |
| `map` to database | Read-only role restricted to approved tables and views. |
| `locations` to `realtime` | Transactional outbox: the event is written in the same transaction as the change and published afterwards. |
| `requests` to `locations` | Calls the `locations` API to change a location status. It never writes to the Geo Store directly. |

---

## 6. Data model

### 6.1 Entity overview

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

| Table | Purpose | Mutability |
|---|---|---|
| `ref_waste_amount_bucket` | Waste-amount buckets (code, label, sort order). Must match the buckets in the project README. | Changed only by migration |
| `ref_road_condition` | Road conditions. Must match the project README. | Changed only by migration |
| `waste_locations` | One row per physical location: the point and the **current** amount, road condition and status. | Updated by the service |
| `location_reports` | Observations. The first report creates the location; later reports update its current values. | Append-only |
| `location_status_history` | Every status transition, with who and when. | Append-only |
| `outbox_events` | Events waiting to be published to the real-time service. | Insert, then mark published |

### 6.2 Reference schema

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
    reported_at        timestamptz NOT NULL,               -- device time
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

### 6.3 Indexes

```sql
-- Spatial: all map and proximity queries
CREATE INDEX waste_locations_geom_gist
    ON waste_locations USING gist (geom);

-- Spatial, open locations only (default map view); optional, measure first
CREATE INDEX waste_locations_geom_open_gist
    ON waste_locations USING gist (geom)
    WHERE status <> 'closed';

-- Filtering by status
CREATE INDEX waste_locations_open_status_idx
    ON waste_locations (status) WHERE status <> 'closed';

-- Reports and history per location, newest first
CREATE INDEX location_reports_location_idx
    ON location_reports (location_id, received_at DESC);
CREATE INDEX location_status_history_location_idx
    ON location_status_history (location_id, changed_at DESC);

-- Outbox publisher
CREATE INDEX outbox_unpublished_idx
    ON outbox_events (id) WHERE published_at IS NULL;
```

`client_request_id` already has a unique index from its `UNIQUE` constraint. That index is what makes ingestion idempotent.

### 6.4 Rationale for storing current values on the location

The map needs one amount and one road condition per point, quickly. Computing them from report history on every request would be slow and complex. The `locations` service updates `amount_bucket`, `road_condition` and `status` in the same transaction that inserts a report or history row. The history tables remain the audit trail and the source for rebuilding current values if required.

---

## 7. Waste-location status lifecycle

States and transitions are **(prov.)** and must be aligned with the state diagram in `docs/requirements/`, including confirmation after collection and reopening after collection.

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

| Rule | Description |
|---|---|
| Validation | Transitions are validated in the service layer. The database enforces the set of allowed values with a `CHECK` constraint. |
| Atomicity | Each transition writes one history row and increments `version` in a single transaction. |
| Reopening | `reopen_count` increases each time a location enters `reopened`. |
| Retention of closed locations | A `closed` location is never deleted. A new report within the duplicate radius (Section 9.3) is treated as a reopening, not a new location. |
| Concurrency | Status changes carry the expected `version`. A mismatch is rejected as a conflict. |

---

## 8. Spatial design decisions

| Topic | Decision | Rationale |
|---|---|---|
| Coordinate system | SRID 4326 (WGS 84, longitude and latitude) | The format delivered by GPS devices and web maps. |
| Stored column type | `geography(Point, 4326)` **(prov.)** | Distances in metres and `ST_DWithin` use the GiST index directly, with no manual projection. |
| Axis order | **Longitude first**, then latitude, everywhere in SQL | `ST_MakePoint(lon, lat)`. Swapped axes are a silent and common defect. |
| Index | GiST on `geom` | Supports bounding box, distance and nearest-neighbour search. |
| Geometry for processing | Cast with `geom::geometry` only where a function requires it (grid aggregation, vector tiles) | Keeps the stored type simple and common queries indexed. |
| Precision | Store full device precision; round on output where privacy requires | See Section 15.3. |

The choice of `geography` over `geometry` affects every query and is tracked as decision D-01 in Section 18.

---

## 9. Query catalogue

Parameters are written as `:name` and must always be bound parameters, never concatenated into SQL.

### 9.1 Insert a point

```sql
INSERT INTO waste_locations (geom, accuracy_m, amount_bucket, first_reported_by)
VALUES (
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
    :accuracy_m, :amount_bucket, :user_id
)
RETURNING id;
```

### 9.2 Locations inside the visible map area

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

### 9.3 Duplicate detection before creating a location

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

### 9.4 Nearest locations to a point

```sql
SELECT id,
       ST_Distance(geom, ref.p) AS distance_m
FROM   waste_locations,
       (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS p) AS ref
WHERE  status <> 'closed'
ORDER  BY geom <-> ref.p
LIMIT  :n;
```

### 9.5 Aggregation for low zoom levels

At low zoom, return one cell per grid square instead of every point. Each cell reports a count and the **worst** amount bucket it contains, so the front end can color it from the palette.

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

The grid size `:cell_deg` is derived from the zoom level by the map service. Server-side vector tiles (`ST_AsMVT`) are an alternative tracked as decision D-04.

### 9.6 Status history of a location

```sql
SELECT from_status, to_status, changed_by, changed_at, note
FROM   location_status_history
WHERE  location_id = :id
ORDER  BY changed_at DESC;
```

---

## 10. Service interface and events

### 10.1 Interface

The Geo Store is reached through the `locations` service. The endpoints below are **(prov.)** and illustrate the intended contract. The authoritative definition is the OpenAPI specification in `docs/api/`.

| Method and path | Purpose |
|---|---|
| `POST /locations/reports` | Submit a report. Creates a location or attaches to an existing one. Idempotent on `client_request_id`. |
| `GET /locations?bbox=minLon,minLat,maxLon,maxLat` | Locations in the visible map area. |
| `GET /locations/clusters?bbox=...&zoom=...` | Aggregated cells for low zoom. |
| `GET /locations/nearby?lon=...&lat=...&limit=...` | Nearest open locations. |
| `GET /locations/{id}` | One location with its current values. |
| `GET /locations/{id}/history` | Status history. |
| `POST /locations/{id}/status` | Request a status transition, validated server-side. |

| Convention | Behaviour |
|---|---|
| Idempotency | Repeating `POST /locations/reports` with the same `client_request_id` returns the original result and creates nothing. |
| Optimistic concurrency | Status changes send the expected `version`. A mismatch returns a conflict response. |
| Error handling | Invalid coordinates, unknown codes and illegal transitions return client errors with a stable error code, never raw database messages. |
| Result limits | Every list endpoint enforces a maximum page or result size. |

### 10.2 Events

| Event type | Emitted when |
|---|---|
| `location.created` | A new location is created. |
| `location.updated` | The current amount or road condition changes. |
| `location.status_changed` | A status transition is recorded. |

Event payloads are defined in `docs/api/`. They carry identifiers and current values, never personal data. Delivery is at least once; consumers must be idempotent.

---

## 11. Data integrity and validation rules

| Rule | Enforced by |
|---|---|
| Longitude between -180 and 180, latitude between -90 and 90 | API validation and database type |
| Optional service-area limit (reject points outside the pilot region) **(prov.)** | API validation, configurable |
| Amount bucket and road condition must exist in the reference tables | Foreign keys |
| A report must carry an amount, a road condition, or both | `CHECK` constraint |
| Accuracy is not negative | `CHECK` constraint |
| Status is one of the allowed values | `CHECK` constraint and service layer |
| Status transitions follow the lifecycle | Service layer, tested |
| One report per `client_request_id` | `UNIQUE` constraint |
| Reports and history are never updated or deleted by the application | Database permissions (no `UPDATE` or `DELETE` granted on these tables) |
| Photo keys match the expected object-storage key pattern and a maximum count | API validation |
| Device time is stored separately from server time; server time is authoritative for ordering | Column design |

---

## 12. Migration policy

| Policy | Detail |
|---|---|
| Tool | Alembic. One concern per migration. |
| Reversibility | Every migration has a working `downgrade()`. CI runs upgrade, downgrade, upgrade. |
| First migration | Creates the PostGIS extension: `CREATE EXTENSION IF NOT EXISTS postgis`. |
| Enumerations | Prefer lookup tables and `CHECK` constraints over native enum types, which are harder to change reversibly. |
| Immutability | A merged migration is never edited. A new migration is added instead. |
| Large indexes | Use `CREATE INDEX CONCURRENTLY` on populated tables, in a migration that runs outside a transaction. |
| Reference data | Seeded by migration. Values must match the project README. |
| Review | Spatial and schema changes require the "Spatial / database changes" section of the pull request template. |

Minimal pattern:

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        CREATE TABLE waste_locations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            geom geography(Point, 4326) NOT NULL
            -- remaining columns as in Section 6.2
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

## 13. Development environment

### 13.1 Prerequisites

Docker, `uv` and `pre-commit` (see the project README).

### 13.2 Local PostGIS database

```yaml
# docker-compose.yml (excerpt)
services:
  db:
    image: postgis/postgis:16-3.4     # pin an exact tag and verify it in the registry
    environment:
      POSTGRES_DB: dwms
      POSTGRES_USER: dwms
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}   # from a local .env, never committed
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

Verify the extension:

```sql
SELECT postgis_full_version();
```

### 13.3 Rules

- `.env` files and credentials are never committed.
- Development and test data is synthetic. Real citizen data is never used outside production.

---

## 14. Testing strategy

| Level | What is verified | Tooling |
|---|---|---|
| Migration | `upgrade`, `downgrade`, `upgrade` succeed on an empty database | `pytest` against a real PostGIS container |
| Repository | Insert, duplicate detection, visible-area, nearest and aggregation queries return correct rows | `pytest` with seeded synthetic points |
| Idempotency | The same `client_request_id` twice creates one report | `pytest` |
| Lifecycle | Every allowed transition succeeds, every other is rejected, history rows are written | `pytest` |
| Plan checks | Production queries use the GiST index (`EXPLAIN` shows an index scan) | `pytest` on a table large enough for the planner to choose the index |
| Contract | Responses match `docs/api/` | Contract test in CI |

Required edge cases: swapped latitude and longitude, points outside the service area, points near the antimeridian and poles, null accuracy, identical coordinates from different users, concurrent status changes on the same location, and duplicate submissions racing each other.

Run before every pull request:

```bash
uv run pytest -q
pre-commit run --all-files
```

---

## 15. Non-functional requirements

### 15.1 Performance targets **(prov.)**

These are targets to be confirmed by measurement, not guarantees.

| Operation | Target at 1 million locations |
|---|---|
| Visible-area query, up to 500 rows | p95 under 100 ms |
| Nearest 20 locations | p95 under 50 ms |
| Duplicate check on insert | p95 under 30 ms |
| Low-zoom aggregation, city-wide | p95 under 300 ms |

Practices: review `EXPLAIN (ANALYZE, BUFFERS)` for every new spatial query; always limit result sizes; run `ANALYZE` after bulk loads; keep autovacuum enabled and monitor bloat; measure the partial GiST index in Section 6.3 against the full index before keeping both; partition `location_reports` and `location_status_history` by time only after measurement shows a need.

### 15.2 Availability and recovery **(prov.)**

| Item | Target |
|---|---|
| Recovery point objective (RPO) | 15 minutes, using write-ahead log archiving |
| Recovery time objective (RTO) | 4 hours |
| Backup restore rehearsal | At least once per term or release cycle |

### 15.3 Security and privacy

| Area | Requirement |
|---|---|
| Personal data | None in the Geo Store. Users are pseudonymous UUIDs only. |
| Location sensitivity | Precise coordinates can reveal a person's whereabouts. Access is role-limited; public views may round coordinates (precision to be decided, D-06). |
| Database roles | Separate roles for `locations` (read/write on its tables), `map` (read-only on approved views) and migrations (schema changes). No application role is a superuser. |
| Queries | Parameterised only. No SQL assembled from user input. |
| Input | Validated at the boundary (Section 11). |
| Transport and storage | TLS to the database outside local development; encrypted backups. |
| Secrets | Read from the environment or a secrets manager. Never committed. |
| Retention | A retention and anonymisation rule for old reports is required (D-06). |

---

## 16. Operations

| Area | Practice |
|---|---|
| Backups | Scheduled base backups plus write-ahead log archiving for point-in-time recovery. Restores are rehearsed. |
| Monitoring | Slow queries (`pg_stat_statements`), connection count, table and index size, replication lag if replicas exist, and outbox backlog (rows with `published_at IS NULL`). |
| Outbox publisher | Polls unpublished events in order, publishes, then sets `published_at`. Must survive restarts and deliver at least once. |
| PostGIS upgrades | Upgrade the package, then `ALTER EXTENSION postgis UPDATE` (or `SELECT postgis_extensions_upgrade()`), after testing on a copy of production data. |
| Index maintenance | `REINDEX` when bloat is measured, not on a calendar. |
| Incident handling | Slow-query and outbox-backlog alerts have a named responder and a runbook entry. |

---

## 17. Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Swapped longitude and latitude corrupt data silently | Medium | High | Single helper for building points, validation, edge-case tests |
| R-02 | Duplicate locations from offline sync and retries | High | Medium | Idempotent `client_request_id`, duplicate-radius check |
| R-03 | Slow map queries as data grows | Medium | High | GiST indexes, result limits, plan checks in CI, aggregation at low zoom |
| R-04 | Divergence between this schema and the API or requirements | Medium | Medium | Contract-first process, traceability table, review against `docs/` |
| R-05 | Location data exposes individuals | Low | High | No personal data, role-limited access, rounding on public views, retention rule |
| R-06 | Irreversible or untested migrations block releases | Medium | High | Mandatory downgrade, up-down-up CI check |
| R-07 | Event loss between database and real-time service | Low | Medium | Transactional outbox, idempotent consumers, backlog alert |
| R-08 | Status rules differ between services | Medium | Medium | Rules owned by `locations` only; `requests` calls its API |
| R-09 | Provisional values treated as final | Medium | Medium | Mark with (prov.), review before implementation, record decisions |

---

## 18. Decision register

Each decision needs a short ADR in `docs/adr/` before implementation.

| ID | Decision | Options | Proposed | Affects |
|---|---|---|---|---|
| D-01 | Stored column type | `geography`, or `geometry` with projection | `geography` | Every spatial query |
| D-02 | Status list and transitions | As in the requirements state diagram | Section 7 (prov.) | Service logic, history, API, events |
| D-03 | Duplicate radius | Fixed value, or tied to GPS accuracy | 15 m fixed (prov.) | Data quality, reopening |
| D-04 | Clustering approach | Server-side grid, `ST_ClusterDBSCAN`, vector tiles with `ST_AsMVT` | Server-side grid | Map service, performance |
| D-05 | Who may change status | Reporter, field agent, operator roles; linked to the SPF create and cancel question | To be decided | Permissions across services |
| D-06 | Retention and rounding | Period and method for old reports; public coordinate precision | To be decided | Privacy, storage |
| D-07 | Event delivery | Polling outbox, logical replication, `LISTEN/NOTIFY` | Polling outbox | Real-time latency and complexity |
| D-08 | Service-area limit | Reject points outside the pilot region, or accept all | Configurable limit | Data quality, abuse prevention |
| D-09 | Editing after submission | Whether a reporter can correct a location or amount | To be decided | History model, API |

---

## 19. Contribution standards and definition of done

### 19.1 Pull request requirements

For any pull request touching the Geo Store:

- Declare **Objective 1**, and **Objective 2** if the map is affected. List `locations` (and `map` if applicable) under services touched.
- Complete the **Spatial / database changes** section of the pull request template.
- Include a **reversible Alembic migration**.
- Show that each new spatial query **uses a GiST index**, with `EXPLAIN ANALYZE` output attached (redact if needed).
- Update `docs/api/` for any request, response or event change, and update this document if the model changes.
- Add tests at the appropriate level (Section 14).
- Contain no secrets, no real citizen data and no hard-coded palette values.
- Disclose any AI assistance and state how it was verified.
- Keep the pull request to one concern and under about 400 changed lines.

### 19.2 Definition of done

A Geo Store change is done when:

1. The migration upgrades and downgrades cleanly in CI.
2. Tests pass at repository, lifecycle and contract level.
3. Query plans show index use and are attached to the pull request.
4. The OpenAPI specification and this document are current.
5. A reviewer from the owning squad and a reviewer from a consuming squad have approved.
6. Any new decision is recorded as an ADR.

---

## Appendix A: Glossary

| Term | Meaning |
|---|---|
| ADR | Architecture decision record: a short document recording a significant design decision. |
| Bounding box | A rectangle defined by minimum and maximum longitude and latitude, used to select what is visible on a map. |
| GiST | Generalized Search Tree: the PostgreSQL index type used for spatial data. |
| Geography | A PostGIS type that stores points on the earth's surface and measures distance in metres. |
| Geometry | A PostGIS type that stores points on a flat plane in a chosen coordinate system. |
| Idempotent | Safe to repeat: doing the same operation twice has the same result as doing it once. |
| MoSCoW | Priority scheme (Must, Should, Could, Won't) used in the requirements document. |
| Outbox | A table of events written in the same transaction as a change, then published to other services. |
| PostGIS | The spatial extension for PostgreSQL. |
| RPO / RTO | Recovery point objective (maximum acceptable data loss) and recovery time objective (maximum acceptable downtime). |
| SPF | The service request handled by the `requests` service. Define it here from the project README glossary. |
| SRID 4326 | The identifier of the WGS 84 longitude and latitude coordinate system. |
