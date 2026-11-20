#!/usr/bin/env bash
set -euo pipefail
trap 'docker compose down' EXIT

docker compose up -d
sleep 60

bad=$(docker compose ps --format '{{.Name}} {{.Status}}' | grep -v '(healthy)' || true)

if [ -n "$bad" ]; then
  echo "FAIL: these services are not healthy:"
  echo "$bad"
  exit 1
fi

echo "PASS: all services are Up (healthy)"