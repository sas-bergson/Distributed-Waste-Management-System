"""User-facing waste report endpoints (Feature 18). Contract: docs/api/locations.yaml."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response

from app.auth import CurrentUser, Principal
from app.config import get_settings
from app.problems import ProblemError, forbidden, invalid, not_found
from app.repository import BBox, Cursor, NewReport, ReportFilters, Repository
from app.schemas import (
    AmountBucket,
    Report,
    ReportCreate,
    ReporterRole,
    ReportPage,
    ReportStatus,
    ReportUpdate,
    Role,
    WasteType,
)

router = APIRouter(prefix="/reports", tags=["reports"])

E = TypeVar("E", bound=StrEnum)


def _tenant(user: Principal) -> str | None:
    return None if user.sees_all_districts else user.tenant_id


def _etag(version: int) -> str:
    return f'"{version}"'


def _parse_list(raw: str | None, kind: type[E], field: str) -> list[E]:
    """Comma-separated query value (OpenAPI style: form, explode: false)."""
    if not raw:
        return []
    try:
        return [kind(item.strip()) for item in raw.split(",") if item.strip()]
    except ValueError:
        allowed = ", ".join(member.value for member in kind)
        raise invalid(field, f"must be one or more of: {allowed}") from None


def _parse_bbox(raw: str | None) -> BBox | None:
    if not raw:
        return None
    try:
        lat_min, lon_min, lat_max, lon_max = (float(part) for part in raw.split(","))
    except ValueError:
        raise invalid("bbox", "must be lat_min,lon_min,lat_max,lon_max") from None
    if not (-90 <= lat_min <= lat_max <= 90 and -180 <= lon_min <= lon_max <= 180):
        raise invalid("bbox", "min values must not exceed max values, within valid coordinates")
    return BBox(lat_min, lon_min, lat_max, lon_max)


@router.post("", status_code=201)
def create_report(
    body: ReportCreate, user: CurrentUser, repo: Repository, response: Response
) -> Report:
    now = datetime.now(UTC)
    observed_at = body.observed_at or now
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    skew = timedelta(seconds=get_settings().jwt_leeway_seconds)
    if observed_at > now + skew:
        raise invalid("observed_at", "must not be in the future")

    report = repo.create(
        NewReport(
            tenant_id=user.tenant_id,
            latitude=body.latitude,
            longitude=body.longitude,
            accuracy_m=body.accuracy_m,
            location_source=body.location_source,
            amount_bucket=body.amount_bucket,
            waste_type=body.waste_type,
            description=body.description,
            reporter_id=user.sub,  # from the token, never from the body
            reporter_role=ReporterRole(user.role.value),
            observed_at=observed_at,
        )
    )
    response.headers["Location"] = f"/reports/{report.id}"
    response.headers["ETag"] = _etag(report.version)
    return report


@router.get("")
def list_reports(
    user: CurrentUser,
    repo: Repository,
    bbox: str | None = None,
    amount_bucket: str | None = None,
    waste_type: str | None = None,
    status: str | None = None,
    updated_since: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    cursor: str | None = None,
) -> ReportPage:
    try:
        position = Cursor.decode(cursor) if cursor else None
    except ValueError:
        raise invalid("cursor", "use the next_cursor value from the previous page") from None

    filters = ReportFilters(
        bbox=_parse_bbox(bbox),
        amount_buckets=_parse_list(amount_bucket, AmountBucket, "amount_bucket"),
        waste_types=_parse_list(waste_type, WasteType, "waste_type"),
        statuses=_parse_list(status, ReportStatus, "status"),
        updated_since=updated_since,
        cursor=position,
        limit=limit,
    )
    items = repo.list(filters, _tenant(user))
    next_cursor = None
    if len(items) > limit:
        items = items[:limit]
        next_cursor = Cursor(items[-1].created_at, items[-1].id).encode()
    return ReportPage(items=items, next_cursor=next_cursor)


@router.get("/{report_id}")
def get_report(report_id: UUID, user: CurrentUser, repo: Repository, response: Response) -> Report:
    report = repo.get(report_id, _tenant(user))
    if report is None:
        raise not_found(f"No report {report_id} in your district")
    response.headers["ETag"] = _etag(report.version)
    return report


def _check_can_update(user: Principal, report: Report, changes: dict[str, object]) -> None:
    if user.role is not Role.CITIZEN:
        return
    if report.reporter.id != user.sub:
        raise forbidden("Citizens can only edit their own reports")
    if set(changes) - {"description"}:
        raise forbidden("Citizens can only change the description")


def _expected_version(if_match: str | None) -> int:
    if if_match is None:
        raise ProblemError(
            428,
            "precondition-required",
            "Precondition required",
            "Send If-Match with the ETag you last read.",
        )
    tag = if_match.strip().removeprefix("W/").strip('"')
    try:
        return int(tag)
    except ValueError:
        return -1  # can't match any version: answered as 412 below


@router.patch("/{report_id}")
def update_report(
    report_id: UUID,
    body: ReportUpdate,
    user: CurrentUser,
    repo: Repository,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
) -> Report:
    expected = _expected_version(if_match)
    tenant = _tenant(user)
    current = repo.get(report_id, tenant)
    if current is None:
        raise not_found(f"No report {report_id} in your district")
    changes = body.changes()
    _check_can_update(user, current, changes)

    updated = repo.update(report_id, tenant, expected, changes)
    if updated is None:
        raise ProblemError(
            412,
            "version-conflict",
            "Report changed since you read it",
            "Reload the report and retry with its new ETag.",
            headers={"ETag": _etag(current.version)},
        )
    response.headers["ETag"] = _etag(updated.version)
    return updated
