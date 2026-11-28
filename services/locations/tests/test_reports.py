import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from tests.conftest import TenantToken, bearer
from tests.fakes import InMemoryReportRepository

pytestmark = pytest.mark.anyio

DOUALA = "district-douala-01"
YAOUNDE = "district-yaounde-01"


def report_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "latitude": 4.0511,
        "longitude": 9.7679,
        "amount_bucket": "high",
        "waste_type": "household",
    }
    body.update(overrides)
    return body


async def create(client: httpx.AsyncClient, token: str, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/reports", json=report_body(**overrides), headers=bearer(token))
    assert response.status_code == 201, response.text
    return dict(response.json())


# ---------- POST /reports ----------


async def test_create_report(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    user_id = str(uuid.uuid4())
    response = await client.post(
        "/reports",
        json=report_body(accuracy_m=8, description="Pile next to the market"),
        headers=bearer(make_token(role="field_agent", sub=user_id)),
    )
    assert response.status_code == 201
    report = response.json()
    assert response.headers["location"] == f"/reports/{report['id']}"
    assert response.headers["etag"] == '"1"'
    assert report["reporter"] == {"id": user_id, "role": "field_agent"}  # from the token
    assert report["status"] == "open"
    assert report["location_source"] == "gps"
    assert report["version"] == 1


async def test_offline_report_keeps_observed_at(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    seen = "2026-11-17T07:45:00Z"
    report = await create(client, make_token(), observed_at=seen, location_source="manual_pin")
    assert report["observed_at"].startswith("2026-11-17T07:45:00")


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"latitude": 200}, "latitude"),
        ({"longitude": -181}, "longitude"),
        ({"amount_bucket": "huge"}, "amount_bucket"),
        ({"waste_type": "spaceship"}, "waste_type"),
        ({"description": "x" * 501}, "description"),
        ({"location_source": "sensor"}, "location_source"),
        ({"reporter_id": "someone-else"}, "reporter_id"),
    ],
)
async def test_invalid_reports_are_422_problems(
    client: httpx.AsyncClient, make_token: TenantToken, overrides: dict[str, Any], field: str
) -> None:
    response = await client.post(
        "/reports", json=report_body(**overrides), headers=bearer(make_token())
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert field in [error["field"] for error in response.json()["errors"]]


async def test_missing_fields_are_listed(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    response = await client.post("/reports", json={}, headers=bearer(make_token()))
    fields = {error["field"] for error in response.json()["errors"]}
    assert {"latitude", "longitude", "amount_bucket", "waste_type"} <= fields


async def test_observed_at_in_the_future_is_rejected(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    response = await client.post(
        "/reports", json=report_body(observed_at=tomorrow), headers=bearer(make_token())
    )
    assert response.status_code == 422


# ---------- GET /reports/{id} and district isolation ----------


async def test_get_report_with_etag(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    created = await create(client, make_token())
    response = await client.get(f"/reports/{created['id']}", headers=bearer(make_token()))
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.headers["etag"] == '"1"'


async def test_unknown_report_is_404(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    response = await client.get(f"/reports/{uuid.uuid4()}", headers=bearer(make_token()))
    assert response.status_code == 404


async def test_other_district_cannot_see_report(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    created = await create(client, make_token(tenant_id=DOUALA))
    yaounde = bearer(make_token(role="supervisor", tenant_id=YAOUNDE))

    assert (await client.get(f"/reports/{created['id']}", headers=yaounde)).status_code == 404
    listed = (await client.get("/reports", headers=yaounde)).json()
    assert listed["items"] == []


async def test_admin_sees_every_district(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    await create(client, make_token(tenant_id=DOUALA))
    await create(client, make_token(tenant_id=YAOUNDE))
    admin = bearer(make_token(role="admin", tenant_id="hq"))
    assert len((await client.get("/reports", headers=admin)).json()["items"]) == 2


# ---------- GET /reports filters and paging ----------


async def test_filters(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    token = make_token()
    in_akwa = await create(client, token, latitude=4.05, longitude=9.70, amount_bucket="overflow")
    await create(client, token, latitude=4.05, longitude=9.70, amount_bucket="low")
    await create(client, token, latitude=3.87, longitude=11.52, amount_bucket="overflow")

    response = await client.get(
        "/reports",
        params={"bbox": "4.0,9.6,4.1,9.8", "amount_bucket": "high,overflow"},
        headers=bearer(token),
    )
    assert response.status_code == 200
    assert [r["id"] for r in response.json()["items"]] == [in_akwa["id"]]


@pytest.mark.parametrize(
    "params",
    [
        {"bbox": "4.1,9.6,4.0,9.8"},  # min above max
        {"bbox": "4.0,9.6"},
        {"amount_bucket": "low,huge"},
        {"status": "resolved"},
        {"cursor": "not-a-cursor"},
        {"limit": 0},
        {"limit": 501},
    ],
)
async def test_bad_list_parameters_are_422(
    client: httpx.AsyncClient, make_token: TenantToken, params: dict[str, Any]
) -> None:
    response = await client.get("/reports", params=params, headers=bearer(make_token()))
    assert response.status_code == 422


async def test_pages_cover_every_report_once_newest_first(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    token = make_token()
    created = [(await create(client, token))["id"] for _ in range(5)]

    seen: list[str] = []
    params: dict[str, Any] = {"limit": 2}
    while True:
        page = (await client.get("/reports", params=params, headers=bearer(token))).json()
        seen += [r["id"] for r in page["items"]]
        if page["next_cursor"] is None:
            break
        params["cursor"] = page["next_cursor"]

    assert seen == list(reversed(created))


async def test_updated_since(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    token = make_token()
    first = await create(client, token)
    second = await create(client, token)
    response = await client.get(
        "/reports", params={"updated_since": first["updated_at"]}, headers=bearer(token)
    )
    assert [r["id"] for r in response.json()["items"]] == [second["id"]]


# ---------- PATCH /reports/{id} ----------


async def patch(
    client: httpx.AsyncClient,
    report_id: str,
    token: str,
    body: dict[str, Any],
    if_match: str | None = '"1"',
) -> httpx.Response:
    headers = bearer(token)
    if if_match is not None:
        headers["If-Match"] = if_match
    return await client.patch(f"/reports/{report_id}", json=body, headers=headers)


async def test_update_bumps_version(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    agent = make_token(role="field_agent")
    created = await create(client, agent)
    response = await patch(client, created["id"], agent, {"amount_bucket": "overflow"})
    assert response.status_code == 200
    assert response.json()["amount_bucket"] == "overflow"
    assert response.json()["version"] == 2
    assert response.headers["etag"] == '"2"'


async def test_missing_if_match_is_428(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    agent = make_token(role="field_agent")
    created = await create(client, agent)
    response = await patch(client, created["id"], agent, {"status": "invalid"}, if_match=None)
    assert response.status_code == 428


async def test_concurrent_updates_do_not_overwrite_each_other(
    client: httpx.AsyncClient, make_token: TenantToken, repo: InMemoryReportRepository
) -> None:
    """Two agents read version 1; the second write must be refused, not silently applied."""
    agent = make_token(role="field_agent")
    created = await create(client, agent)

    first = await patch(client, created["id"], agent, {"amount_bucket": "overflow"})
    second = await patch(client, created["id"], agent, {"amount_bucket": "empty"})

    assert first.status_code == 200
    assert second.status_code == 412
    assert second.headers["etag"] == '"2"'
    stored = repo.get(uuid.UUID(created["id"]), None)
    assert stored is not None and stored.amount_bucket == "overflow"


async def test_status_lifecycle_values(client: httpx.AsyncClient, make_token: TenantToken) -> None:
    supervisor = make_token(role="supervisor")
    created = await create(client, supervisor)
    response = await patch(client, created["id"], supervisor, {"status": "collection_requested"})
    assert response.json()["status"] == "collection_requested"


async def test_citizen_can_edit_own_description_only(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    me = str(uuid.uuid4())
    citizen = make_token(role="citizen", sub=me)
    created = await create(client, citizen)

    ok = await patch(client, created["id"], citizen, {"description": "Bigger now"})
    assert ok.status_code == 200
    status_change = await patch(client, created["id"], citizen, {"status": "collected"}, '"2"')
    assert status_change.status_code == 403


async def test_citizen_cannot_edit_someone_elses_report(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    created = await create(client, make_token(role="citizen"))
    stranger = make_token(role="citizen")
    response = await patch(client, created["id"], stranger, {"description": "mine now"})
    assert response.status_code == 403


@pytest.mark.parametrize(
    "body",
    [{}, {"amount_bucket": None}, {"latitude": 1.0}, {"status": "resolved"}],
    ids=["empty", "null-bucket", "location-is-immutable", "unknown-status"],
)
async def test_invalid_updates_are_422(
    client: httpx.AsyncClient, make_token: TenantToken, body: dict[str, Any]
) -> None:
    agent = make_token(role="field_agent")
    created = await create(client, agent)
    assert (await patch(client, created["id"], agent, body)).status_code == 422


async def test_update_in_other_district_is_404(
    client: httpx.AsyncClient, make_token: TenantToken
) -> None:
    created = await create(client, make_token(tenant_id=DOUALA))
    outsider = make_token(role="supervisor", tenant_id=YAOUNDE)
    response = await patch(client, created["id"], outsider, {"status": "invalid"})
    assert response.status_code == 404
