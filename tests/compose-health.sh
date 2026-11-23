#!/usr/bin/env bash
# Feature 1 TEST: every compose service must report (healthy).
set -uo pipefail
cd "$(dirname "$0")/.."

if [ ! -f docker-compose.yml ] && [ ! -f compose.yaml ]; then
  echo "FAIL: no docker-compose.yml found in $(pwd)"
  exit 1
fi

trap 'docker compose down' EXIT
docker compose up -d || { echo "FAIL: docker compose up failed"; exit 1; }

echo "Waiting 60s for services to become healthy..."
sleep 60

echo "--- service status ---"
docker compose ps --format '{{.Name}}: {{.Status}}'

bad=$(docker compose ps --format '{{.Name}}: {{.Status}}' | grep -v '(healthy)' || true)
if [ -n "$bad" ]; then
  echo "FAIL: services not healthy:"
  echo "$bad"
  exit 1
fi
echo "PASS: all services are Up (healthy)"