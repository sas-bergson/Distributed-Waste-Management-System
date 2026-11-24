#!/usr/bin/env bash
set -euo pipefail

PROM_URL="${PROM_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3002}"
GRAFANA_USER="${GF_SECURITY_ADMIN_USER:-admin}"
GRAFANA_PASS="${GF_SECURITY_ADMIN_PASSWORD:-change-me-local-dev-only}"

echo "Checking Prometheus health at ${PROM_URL}/-/healthy..."
curl -fsS "${PROM_URL}/-/healthy" >/dev/null

echo "Checking Prometheus targets API..."
curl -fsS "${PROM_URL}/api/v1/targets" | grep -q '"status":"success"'

echo "Checking Grafana health at ${GRAFANA_URL}/api/health..."
curl -fsS "${GRAFANA_URL}/api/health" | grep -q '"database":"ok"'

echo "Checking Grafana Prometheus datasource..."
curl -fsS -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  "${GRAFANA_URL}/api/datasources/uid/dwms-prometheus" >/dev/null

echo "Checking Grafana DWMS overview dashboard..."
curl -fsS -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  "${GRAFANA_URL}/api/dashboards/uid/dwms-overview" >/dev/null

echo "All observability metrics-visible checks passed."
