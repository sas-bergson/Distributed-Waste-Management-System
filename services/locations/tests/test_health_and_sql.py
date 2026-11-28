import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.dialects import postgresql

from app.repository import BBox, Cursor, ReportFilters, build_list_query
from app.schemas import AmountBucket
from tests.fakes import InMemoryReportRepository


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/healthz", "/health"])
async def test_health(client: httpx.AsyncClient, repo: InMemoryReportRepository, path: str) -> None:
    ok = await client.get(path)
    assert ok.status_code == 200
    assert ok.json() == {"status": "ok", "service": "locations", "database": "reachable"}

    repo.database_up = False
    down = await client.get(path)
    assert down.status_code == 503
    assert down.json()["database"] == "unreachable"


def test_cursor_round_trip() -> None:
    cursor = Cursor(datetime(2026, 11, 27, 8, 30, tzinfo=UTC), uuid.uuid4())
    assert Cursor.decode(cursor.encode()) == cursor


def test_list_query_uses_postgis_and_district_filter() -> None:
    """The SQL the PostGIS repository sends, compiled without a database."""
    filters = ReportFilters(
        bbox=BBox(4.0, 9.6, 4.1, 9.8),
        amount_buckets=[AmountBucket.HIGH],
        cursor=Cursor(datetime(2026, 11, 27, tzinfo=UTC), uuid.uuid4()),
        limit=50,
    )
    sql = str(build_list_query(filters, "district-douala-01").compile(dialect=postgresql.dialect()))

    assert "ST_Intersects(locations.waste_reports.location, ST_MakeEnvelope(" in sql
    assert "locations.waste_reports.tenant_id = " in sql
    assert "(locations.waste_reports.created_at, locations.waste_reports.id) < " in sql
    order = "ORDER BY locations.waste_reports.created_at DESC, locations.waste_reports.id DESC"
    assert order in sql
    assert "LIMIT" in sql


def test_admin_list_query_has_no_district_filter() -> None:
    sql = str(build_list_query(ReportFilters(), None).compile(dialect=postgresql.dialect()))
    assert "tenant_id =" not in sql
