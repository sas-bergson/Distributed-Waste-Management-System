"""Tests for Feature 4 (Observability stack) Prometheus and Grafana configs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PROM_DIR = REPO_ROOT / "infra" / "observability" / "prometheus"
GRAFANA_DIR = REPO_ROOT / "infra" / "observability" / "grafana"

EXPECTED_SERVICE_JOBS = {
    "gateway",
    "locations",
    "map",
    "requests",
    "realtime",
    "notifications",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"Missing expected config file: {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"Expected YAML mapping in {path}"
    return data


def test_prometheus_scrape_jobs_cover_all_dwms_services() -> None:
    """Prometheus config must define scrape jobs for all six DWMS services."""
    config = _load_yaml(PROM_DIR / "prometheus.yml")
    scrape_configs = config.get("scrape_configs", [])
    assert isinstance(scrape_configs, list)

    job_names = {
        entry["job_name"]
        for entry in scrape_configs
        if isinstance(entry, dict) and "job_name" in entry
    }
    missing = EXPECTED_SERVICE_JOBS - job_names
    assert not missing, f"Missing Prometheus scrape jobs: {sorted(missing)}"


def test_prometheus_alert_rules_defined() -> None:
    """Prometheus alerts.yml must define at least one alert rule group."""
    alerts = _load_yaml(PROM_DIR / "alerts.yml")
    groups = alerts.get("groups", [])
    assert isinstance(groups, list) and len(groups) > 0

    rule_count = sum(
        len(group.get("rules", []))
        for group in groups
        if isinstance(group, dict)
    )
    assert rule_count > 0, "Expected at least one Prometheus alert rule"


def test_grafana_datasource_and_dashboard_provisioned() -> None:
    """Grafana must provision a default Prometheus datasource and overview dashboard."""
    ds_config = _load_yaml(
        GRAFANA_DIR / "provisioning" / "datasources" / "prometheus.yml"
    )
    datasources = ds_config.get("datasources", [])
    assert isinstance(datasources, list) and len(datasources) > 0
    assert any(
        isinstance(ds, dict) and ds.get("type") == "prometheus" and ds.get("isDefault")
        for ds in datasources
    ), "Expected a default Prometheus datasource in Grafana provisioning"

    dashboard_path = GRAFANA_DIR / "dashboards" / "dwms-overview.json"
    assert dashboard_path.is_file(), f"Missing dashboard: {dashboard_path}"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = dashboard.get("panels", [])
    assert isinstance(panels, list) and len(panels) > 0, (
        "Expected at least one panel in dwms-overview.json"
    )
