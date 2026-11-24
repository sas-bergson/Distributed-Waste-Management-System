# Distributed Waste Management System (DWMS) Documentation

Welcome to the DWMS documentation portal. This site is built from the repository's Markdown documentation using MkDocs.

## Project Objectives

1. **Objective 1 — Collect waste-location information:** Capture geographic waste deposits, fill levels, waste types, and telemetry from citizens, field agents, and IoT smart bins.
2. **Objective 2 — Color-coded map:** Render reported waste locations and serving road conditions using the versioned DWMS palette specification.
3. **Objective 3 — Real-time cloud service:** Expose an authenticated API and live WebSocket/SSE channel to view/update the map and dispatch SPF collection requests.

## Platform Architecture

DWMS runs six containerized services (`gateway`, `locations`, `map`, `requests`, `realtime`, `notifications`) backed by PostgreSQL + PostGIS, Redis, and Mosquitto MQTT.

## Local Preview

```bash
pip install -r docs/site/requirements.txt
mkdocs serve -f docs/site/mkdocs.yml
```
