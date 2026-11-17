# DWMS Microservices Inventory

## Status and scope

This document records the architecture described by the repository documentation. It is an inventory of the **planned** service boundaries, not a claim that those services are implemented.

At the time of writing, `main` contains project documentation and environment conventions only. The paths below (`services/`, `frontend/`, `infrastructure/`, and `tests/`) are described by the README and CONTRIBUTING guide but are not present in the repository yet.

## Runtime service boundaries

The platform has six intended independently deployable runtime services:

| Service | Planned path | Runtime | Internal address | Responsibility | Data or integrations |
|---|---|---|---|---|---|
| API Gateway | `services/gateway/` | TypeScript + Fastify | `localhost:8080` | Public entry point; authentication, authorization, CORS, rate limiting, and routing | JWT; routes to the domain services |
| Location Reporting | `services/locations/` | Python + FastAPI | `locations:8001` | Accepts and validates waste-location reports from people and IoT bins | PostgreSQL/PostGIS `locations` schema; MQTT subscriber; location events |
| Map | `services/map/` | Python + FastAPI | `map:8002` | Returns viewport-scoped GeoJSON or tiles and applies waste-volume and road-condition styling | Location data through an approved service/event boundary; Redis viewport cache; `style/palette.json` |
| SPF Requests | `services/requests/` | Python + FastAPI | `requests:8003` | Creates and tracks collection requests through `REQUESTED`, `ASSIGNED`, `IN_PROGRESS`, and `COLLECTED` (plus `REJECTED` and `CANCELLED`) | PostgreSQL/PostGIS `requests` schema; notification dispatch; request events |
| Real-Time Channel | `services/realtime/` | TypeScript + Node (`ws` or Socket.IO) | `realtime:8004` internally | Publishes map changes and SPF request status changes to connected clients | Redis Pub/Sub fan-out; WebSocket or Server-Sent Events |
| Notification Worker | `services/notifications/` | Python worker (`arq` or Celery) | Worker; no public port specified | Delivers SPF dispatches and status changes through email, SMS, or push providers | Redis/job queue; SMTP and provider integrations |

### What counts as a microservice here

The six rows above own a runtime process, a clear responsibility, and a service boundary. The gateway and the five domain/worker services are therefore the microservices or independently deployed service processes described by the project.

The README's architecture table also lists **Geo Store (PostGIS)** and **Palette & Style Config**. Those are supporting components, not separate microservices:

| Supporting component | Role | Why it is not a service boundary |
|---|---|---|
| PostgreSQL + PostGIS (Geo Store) | Spatial persistence, viewport filtering, and nearest-neighbour queries | A data store owned by the relevant services, not an independently routed application process |
| `palette.json` (Palette & Style Config) | Versioned source of truth for map colours and road-condition styles | Configuration loaded by the Map service, not a network service |
| Redis | Cache and real-time Pub/Sub backplane | Infrastructure shared by Map and Real-Time services |
| Mosquitto/MQTT | IoT transport for smart-bin telemetry | Infrastructure consumed by Location Reporting |

The dashboard and reporter applications, IoT and field-report simulators, PostgreSQL, Redis, MQTT, Docker, Kubernetes, and Terraform are clients, infrastructure, or tooling. They are not counted as microservices.

## Request and event flows

### Waste report ingestion

1. A citizen, field agent, or smart-bin sends a report through the gateway (or through the MQTT ingestion path for telemetry).
2. Location Reporting validates the payload and writes it to its PostGIS schema.
3. Location Reporting publishes a location-change event for Map and Real-Time consumers.
4. Map serves the relevant viewport data; Real-Time broadcasts the change to subscribed clients.

### Map viewing

1. A dashboard requests a viewport through the gateway.
2. The gateway routes the request to Map.
3. Map obtains location and road data through an approved service or read-model boundary, applies the versioned palette, and returns GeoJSON or tiles.
4. Redis may cache the viewport result for the configured TTL.

### SPF dispatch

1. An operator creates a request for a waste location through the gateway.
2. SPF Requests validates the request, stores its state and audit trail, and emits a status event.
3. Notification Worker consumes the dispatch job and sends the configured notification.
4. Real-Time publishes request status changes to the dashboard and reporter clients.

## Ownership rules

- A service must not query another service's database directly.
- Cross-service data must travel through HTTP APIs, events, or the real-time channel.
- Locations owns the `locations` schema; SPF Requests owns the `requests` schema.
- Spatial queries should use PostGIS functions and a GiST index.
- Map styling must load from the versioned palette configuration rather than hard-coded frontend colours.
- Every service should eventually provide a `GET /healthz` endpoint, a Dockerfile, and a pinned Compose service definition.

## Repository implementation audit

The current repository does not yet contain executable implementations for these boundaries. In particular, the following are planned but absent from `main`:

- `docker-compose.yml`
- `services/`
- `frontend/`
- `simulator/`
- `infrastructure/`
- `docs/api/`
- `tests/`

This means the current architecture can be reviewed as a design contract, but it cannot yet be started with the `docker compose up --build` command described in the README.

## Decisions to settle before implementation

1. The environment template names the Real-Time service as `realtime:8004`, while the browser-facing `VITE_REALTIME_URL` uses `ws://localhost:8081`. The internal and public ports should be documented separately or made consistent.
2. The Map service needs an explicit read path for location data that respects the no-cross-database rule: a Location API, an event-built read model, or another documented approach.
3. The gateway's routing contract and the MQTT-to-Location ingestion path need OpenAPI and event-schema definitions before implementation.
4. The Notification Worker needs a queue/topic contract and retry/dead-letter policy.
