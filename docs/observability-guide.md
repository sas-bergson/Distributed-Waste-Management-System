# Observability Stack Guide — Prometheus & Grafana

## 1. Overview
This guide documents the observability architecture for the **Distributed Waste Management System (DWMS)**, built around **Prometheus** (`v2.54.1`) for metrics collection and alerting, and **Grafana** (`11.2.2`) for real-time visualization.

### Repository Layout
```text
infra/observability/
├── prometheus/
│   ├── compose.yml        # Prometheus service & dwms-net network attachment
│   ├── prometheus.yml     # Global scrape config & target definitions
│   └── alerts.yml         # Alerting rules (service health, 5xx rate, p99 latency)
└── grafana/
    ├── compose.yml        # Grafana service (mapped to host port 3002)
    ├── dashboards/
    │   └── dwms-overview.json
    └── provisioning/
        ├── dashboards/
        │   └── provider.yml
        └── datasources/
            └── prometheus.yml

Core Services & Ports
Service: Prometheus, Image: prom/prometheus:v2.54.1, Host Port: 9090; Container Port: 9090; Internal URL: http://prometheus:9090
Service: grafana, Image: grafana/grafana:11.2.2, Host Port: 3002; Container Port: 3000; Internal URL: http://grafana:3000

2. Prerequisites & Network Setup
Both Compose stacks attach to the external Docker bridge network dwms-net. Ensure the core platform stack is running (or create the network manually before starting observability services):
docker network create dwms-net 2>/dev/null || true

3. Starting the Observability Stack 
Prometheus and Grafana are defined in dedicated Compose files under infra/observability/:
# Start Prometheus
docker compose -f infra/observability/prometheus/compose.yml up -d

# Start Grafana
docker compose -f infra/observability/grafana/compose.yml up -d
Verify Health Checks
Both services include built-in Docker health checks:
- Prometheus: http://127.0.0.1:9090/-/healthy
- Grafana: http://127.0.0.1:3000/api/health
Check container health status:docker compose -f infra/observability/prometheus/compose.yml ps
docker compose -f infra/observability/grafana/compose.yml ps

4. Prometheus Configuration & Alerting
Scrape Targets (infra/observability/prometheus/prometheus.yml)
Prometheus scrapes /metrics every 15s across the following jobs and objective labels:
Job Name: prometheus; Target: localhost:9090; Service Label: /; Objective Label: /
Job Name: gateway; Target: gateway:8080; Service Label: gateway; Objective Label: platform
Job Name: locations; Target: locations:8001; Service Label: locations; Objective Label: obj1
Job Name: map; Target: map:8002; Service Label: map; Objective Label: obj2
Job Name: requests; Target: requests:8003; Service Label: requests; Objective Label: obj3
Job Name: realtime; Target: realtime:8004; Service Label: realtime; Objective Label: obj3
Job Name: notifications; Target: notifications:8005; Service Label: notifications; Objective Label: obj3

Alerting Rules (infra/observability/prometheus/alerts.yml)
Group dwms-service-health evaluates three rules:
1. DWMSServiceDown (critical): up == 0 for 1m — target instance is unreachable.
2. DWMSHighErrorRate (warning): 5xx error ratio (http_requests_total{status=~"5.."}) exceeds 5% (> 0.05) over 5m.
3. DWMSHighLatencyP99 (warning): p99 latency (http_request_duration_seconds_bucket) exceeds 500 ms (> 0.5) over 5m.

5. Grafana Provisioning & Dashboards
Access & Credentials
- Web UI: http://localhost:3002
- Default Username: admin (configurable via GF_SECURITY_ADMIN_USER)
- Default Password: change-me-local-dev-only (override via GF_SECURITY_ADMIN_PASSWORD in .env)
- User Sign-up: Disabled (GF_USERS_ALLOW_SIGN_UP="false")

Provisioned Datasource & Dashboard
- Datasource (prometheus.yml): UID dwms-prometheus, default proxy datasource pointing to http://prometheus:9090 (POST, timeInterval: 15s, editable: false).
- Dashboard (DWMS Service Overview, UID dwms-overview): Located in folder DWMS (refresh: 15s, allowUiUpdates: false), containing four panels:
	1. Service Up Status (stat): up{job=~"gateway|locations|map|requests|realtime|notifications"}
	2. Request Rate by Service (req/s) (timeseries): sum by (job) (rate(http_requests_total[1m]))
	3. 5xx Error Rate by Service (timeseries): sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
	4. p99 Request Latency (seconds) (timeseries): histogram_quantile(0.99, sum by (job, le) (rate(http_request_duration_seconds_bucket[5m])))

6. Verification & Troubleshooting (metrics-visible)
Verify Scrape Targets
	1.Open http://localhost:9090/targets or run: curl -s http://localhost:9090/api/v1/targets | grep -E '"scrapeUrl"|"health"'
	2. Confirm all active services show "health": "up".
Common Issues
Symptom:network dwms-net declared as external, but could not be found; Cause: Core Compose stack not started yet; Resolution: Run docker network create dwms-net or start the main docker-compose.yml first
Symptom:Target state is DOWN (connection refused); Cause: Microservice container is not running on dwms-net; Resolution: Check service status and ensure it shares the dwms-net network
Symptom:Target state is DOWN (404 Not Found); Cause: /metrics endpoint not exposed on the microservice; Resolution: Verify Prometheus metrics middleware is mounted at /metrics
Symptom:Grafana panels show No data; Cause: Microservice have not received HTTP traffic yet; Resolution: Send test requests through gateway:8080 so http_requests_total and duration buckets populate