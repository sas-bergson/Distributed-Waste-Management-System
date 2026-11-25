# DWMS Observability Stack Guide

## Overview

This guide documents the local observability stack for the Distributed Waste Management System (DWMS), built with **Prometheus (2.54.1)** and **Grafana (11.2.2)**. Both services attach to the external dwms-net Docker network to collect metrics and visualize health, traffic, error rates, and latency across all core platform services.

## Directory Structure

```text
infra/observability/
├── prometheus/
│   ├── compose.yml
│   ├── prometheus.yml
│   └── alerts.yml
└── grafana/
    ├── compose.yml
    └── provisioning/
        ├── datasources/
        │   └── datasource.yml
        └── dashboards/
            ├── provider.yml
            └── dwms-overview.json
```

## Prerequisites

- Docker and Docker Compose v2 installed locally.
- The shared external network dwms-net must exist before starting the observability stack (created automatically when running the root docker-compose.yml, or manually if starting observability standalone):

```bash
docker network create dwms-net
```

## Local Startup & Verification

### 1. Start Prometheus and Grafana

```bash
docker compose -f infra/observability/prometheus/compose.yml up -d
docker compose -f infra/observability/grafana/compose.yml up -d
```

### 2. Check Container Health Status

```bash
docker compose -f infra/observability/prometheus/compose.yml ps
docker compose -f infra/observability/grafana/compose.yml ps
```

### 3. Verify Endpoints

| Component | Host Endpoint | Internal Container Port | Purpose |
| :--- | :--- | :--- | :--- |
| Prometheus UI | http://localhost:9090 | 9090 | Targets, PromQL queries, alert rules |
| Prometheus Health | http://localhost:9090/-/healthy | 9090 | Liveness/readiness check |
| Grafana UI | http://localhost:3002 | 3000 | Dashboards (dmin / dmin by default) |
| Grafana Health | http://localhost:3002/api/health | 3000 | Host healthcheck endpoint (3000 is internal) |

## Scrape Targets

Prometheus scrapes /metrics every **15 seconds** across all six DWMS services on dwms-net:

| Job Name | Target | Objective Label | Service Role |
| :--- | :--- | :--- | :--- |
| gateway | gateway:8080 | core | API Gateway |
| locations | locations:8001 | 1 | Waste-location collection |
| map | map:8002 | 2 | Color-coded waste & road condition map |
| equests | equests:8003 | 3 | Collection request processing |
| ealtime | ealtime:8004 | 3 | Live map updates & SPF routing |
| 
otifications | 
otifications:8005 | 3 | Alerts & user notifications |

## Alerting Rules (lerts.yml)

| Alert Name | Condition | For | Severity | Description |
| :--- | :--- | :--- | :--- | :--- |
| DWMSServiceDown | up == 0 | 1m | critical | Target service is unreachable or down |
| DWMSHighErrorRate | 5xx error ratio > 5% over 5m | 2m | warning | Elevated HTTP 5xx server error rate |
| DWMSHighLatencyP99 | p99 request latency > 1s over 5m | 5m | warning | 99th percentile latency exceeds 1 second |

## Provisioned Grafana Dashboard

Grafana automatically provisions the dwms-prometheus datasource and loads the **DWMS Service Overview** (dwms-overview) dashboard with four panels:

1. **Service Up** (up)
2. **Request Rate** (ate(http_requests_total[5m]))
3. **5xx Error Rate** (5xx ratio over 5m)
4. **p99 Latency** (histogram_quantile(0.99, ...))

## Troubleshooting

- **
etwork dwms-net declared as external, but could not be found:** Start the main stack (docker compose up -d) or run docker network create dwms-net first.
- **Targets showing DOWN in Prometheus (http://localhost:9090/targets):** Ensure the backend microservices are running on dwms-net and exposing /metrics on their configured ports.
- **Port 3002 or 9090 already in use:** Check for conflicting local processes or stop existing containers with docker compose down.
