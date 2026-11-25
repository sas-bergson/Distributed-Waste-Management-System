# Distributed Tracing Infrastructure (`infra/observability/tracing`)

This directory houses the OpenTelemetry (OTel) Collector and Jaeger tracing infrastructure for DWMS (Feature 5: Distributed Tracing, role **IMP**).

---

## Architecture Overview

The tracing pipeline enables distributed context propagation across:
1. **API Gateway** (`services/gateway` - Node.js/Fastify)
2. **Backend Microservices** (`services/locations`, `services/map`, `services/requests`, `services/notifications` - Python/FastAPI)
3. **Database & Spatial Queries** (PostgreSQL / PostGIS / Redis)

Tracing spans are exported via the **W3C TraceContext** format (`traceparent` HTTP header) to the central OpenTelemetry Collector, which batches, sanitizes, and forwards traces to the **Jaeger** backend.

---

## Exposed Ports

| Component | Port | Protocol | Purpose |
| :--- | :--- | :--- | :--- |
| **Jaeger UI** | `16686` | HTTP | Web UI to search, visualize, and inspect traces |
| **OTel Collector** | `4317` | gRPC | Standard OTLP gRPC ingestion endpoint |
| **OTel Collector** | `4318` | HTTP | Standard OTLP HTTP ingestion endpoint |
| **Collector Metrics**| `8888` | HTTP | OpenTelemetry Collector internal metrics |

---

## How to Run Locally

To spin up the tracing stack independently:

```bash
docker compose -f Platform/infra/observability/tracing/docker-compose.tracing.yml up -d
```

Access the Jaeger UI at: **http://localhost:16686**

---

## Microservice Instrumentation Reference

Services connect to the collector by configuring standard OTel environment variables in `.env`:

### Python (FastAPI / GeoAlchemy2)
```bash
OTEL_SERVICE_NAME=locations-service
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_PROPAGATORS=tracecontext,baggage
```

### Node.js (Fastify / TypeScript)
```bash
OTEL_SERVICE_NAME=gateway-service
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
OTEL_PROPAGATORS=tracecontext,baggage
```
