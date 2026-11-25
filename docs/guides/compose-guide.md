# Local Development in 5 Minutes (Docker Compose)

This guide walks you through starting the entire Distributed Waste Management System (DWMS) stack locally using Docker Compose v2.

## Prerequisites

- **Docker Engine 24+** with **Docker Compose v2** (`docker compose` subcommand, not `docker-compose`)
- **Git**

Verify your Docker Compose version before starting:

```bash
docker compose version
```

## Step 1: Clone and Configure Environment

1. Clone the repository and move into the project root:

   ```bash
   git clone https://github.com/sas-bergson/Distributed-Waste-Management-System.git
   cd Distributed-Waste-Management-System
   ```

2. Create your local `.env` file from the template:

   ```bash
   cp .env.example .env
   ```

   Never commit `.env` to Git. It is already listed in `.gitignore`.

## Step 2: Start the Stack

Start all nine containers in detached mode:

```bash
docker compose up -d
```

The first run downloads the container images. `postgis/postgis:16-3.4` is the largest image (a few hundred MB), so allow a minute or two on the initial pull.

## Step 3: Wait and Verify Container Health

Wait about **60 seconds** for `postgis`, `redis`, `mosquitto`, and the dependent services to pass their health checks, then check their status:

```bash
docker compose ps
```

All **nine** rows should report `(healthy)` in the `STATUS` column.

Once `gateway` is healthy, confirm it is reachable on port `8080`:

```bash
curl -i http://localhost:8080/
```

## What Is Running

The `docker-compose.yml` stack starts **9 containers** (3 infrastructure stores/brokers and 6 application services):

| Container | Image | Purpose | Dependencies / Ports |
| :--- | :--- | :--- | :--- |
| `postgis` | `postgis/postgis:16-3.4` | Spatial database (PostgreSQL 16 + PostGIS 3.4) | Persisted in `postgis-data` volume |
| `redis` | `redis:7-alpine` | Pub/Sub backplane and viewport cache | Healthcheck via `redis-cli ping` |
| `mosquitto` | `eclipse-mosquitto:2` | MQTT broker for IoT bin telemetry | Config at `infrastructure/mosquitto/mosquitto.conf` (listener `1883`) |
| `locations` | `nginx:alpine` (placeholder) | Objective 1 — waste-location reporting | Depends on `postgis`, `mosquitto` |
| `map` | `nginx:alpine` (placeholder) | Objective 2 — viewport GeoJSON and styling | Depends on `postgis` |
| `requests` | `nginx:alpine` (placeholder) | Objective 3 — SPF request lifecycle | Depends on `postgis`, `redis` |
| `realtime` | `nginx:alpine` (placeholder) | Objective 3 — WebSocket/SSE live hub | Depends on `redis` |
| `notifications` | `nginx:alpine` (placeholder) | Objective 3 — async dispatch worker | Depends on `redis` |
| `gateway` | `nginx:alpine` (placeholder) | Single API entry point | Exposes `8080:80`; depends on all 5 app services |

## Replacing Placeholder Services

Until each service team ships its own `Dockerfile`, the six application containers run `nginx:alpine` placeholders. When a service is ready in `services/<name>/`, its maintainer replaces `image: nginx:alpine` in `docker-compose.yml` with:

```yaml
build: ./services/<name>
```

Every real service must expose a `GET /healthz` endpoint so Compose health checks continue to pass.

## Stopping and Resetting

Stop and remove the containers while keeping your PostGIS database volume:

```bash
docker compose down
```

Stop the containers **and** delete the `postgis-data` volume for a clean database reset:

```bash
docker compose down -v
```

## Troubleshooting

- **`docker compose` command not found:** Ensure you have Docker Compose v2 installed (`docker compose`, with a space, not the legacy `docker-compose` v1 binary).
- **Port `8080` already in use:** Stop any local process listening on `8080` before starting `gateway`.
- **Service stays in `(health: starting)`:** Wait the full 60 seconds on first boot while `postgis` initializes its data directory, then inspect logs with `docker compose logs -f <service>`.
- **Mosquitto fails to start:** Confirm `infrastructure/mosquitto/mosquitto.conf` exists and is readable.
