"""Storage of waste reports. The routes only talk to `ReportRepository`."""

import base64
import binascii
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any, Protocol
from uuid import UUID

from fastapi import Depends
from sqlalchemy import Select, func, select, text, tuple_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import WasteReportRow
from app.schemas import (
    AmountBucket,
    LocationSource,
    Report,
    Reporter,
    ReporterRole,
    ReportStatus,
    WasteType,
)


@dataclass(frozen=True)
class NewReport:
    tenant_id: str
    latitude: float
    longitude: float
    accuracy_m: float | None
    location_source: LocationSource
    amount_bucket: AmountBucket
    waste_type: WasteType
    description: str | None
    reporter_id: str
    reporter_role: ReporterRole
    observed_at: datetime


@dataclass(frozen=True)
class BBox:
    lat_min: float
    lon_min: float
    lat_max: float
    lon_max: float


@dataclass(frozen=True)
class Cursor:
    """Position after the last report of a page (newest-first order)."""

    created_at: datetime
    id: UUID

    def encode(self) -> str:
        raw = json.dumps({"c": self.created_at.isoformat(), "i": str(self.id)})
        return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str) -> "Cursor":
        """Raises ValueError on anything that isn't a cursor we issued."""
        try:
            raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
            data = json.loads(raw)
            return cls(created_at=datetime.fromisoformat(data["c"]), id=UUID(data["i"]))
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
            raise ValueError("not a valid cursor") from None


@dataclass(frozen=True)
class ReportFilters:
    bbox: BBox | None = None
    amount_buckets: list[AmountBucket] = field(default_factory=list)
    waste_types: list[WasteType] = field(default_factory=list)
    statuses: list[ReportStatus] = field(default_factory=list)
    updated_since: datetime | None = None
    cursor: Cursor | None = None
    limit: int = 100


class ReportRepository(Protocol):
    """`tenant_id=None` means every district (admin)."""

    def create(self, new: NewReport) -> Report: ...

    def get(self, report_id: UUID, tenant_id: str | None) -> Report | None: ...

    def list(self, filters: ReportFilters, tenant_id: str | None) -> list[Report]:
        """Newest first, at most `filters.limit + 1` items (the extra one means "more pages")."""
        ...

    def update(
        self,
        report_id: UUID,
        tenant_id: str | None,
        expected_version: int,
        changes: dict[str, object],
    ) -> Report | None:
        """Compare-and-set: applies only if the stored version is still `expected_version`."""
        ...

    def ping(self) -> bool: ...


_ROW_COLUMNS = (
    WasteReportRow,
    func.ST_Y(WasteReportRow.location).label("latitude"),
    func.ST_X(WasteReportRow.location).label("longitude"),
)


def _to_report(row: WasteReportRow, latitude: float, longitude: float) -> Report:
    return Report(
        id=row.id,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=row.accuracy_m,
        location_source=LocationSource(row.location_source),
        amount_bucket=AmountBucket(row.amount_bucket),
        waste_type=WasteType(row.waste_type),
        description=row.description,
        status=ReportStatus(row.status),
        reporter=Reporter(id=row.reporter_id, role=ReporterRole(row.reporter_role)),
        observed_at=row.observed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )


def _in_tenant(stmt: Select[Any], tenant_id: str | None) -> Select[Any]:
    return stmt if tenant_id is None else stmt.where(WasteReportRow.tenant_id == tenant_id)


def build_list_query(filters: ReportFilters, tenant_id: str | None) -> Select[Any]:
    stmt = _in_tenant(select(*_ROW_COLUMNS), tenant_id)
    if filters.bbox:
        b = filters.bbox
        envelope = func.ST_MakeEnvelope(b.lon_min, b.lat_min, b.lon_max, b.lat_max, 4326)
        stmt = stmt.where(func.ST_Intersects(WasteReportRow.location, envelope))  # GiST index
    if filters.amount_buckets:
        stmt = stmt.where(WasteReportRow.amount_bucket.in_(filters.amount_buckets))
    if filters.waste_types:
        stmt = stmt.where(WasteReportRow.waste_type.in_(filters.waste_types))
    if filters.statuses:
        stmt = stmt.where(WasteReportRow.status.in_(filters.statuses))
    if filters.updated_since:
        stmt = stmt.where(WasteReportRow.updated_at > filters.updated_since)
    if filters.cursor:
        position = (filters.cursor.created_at, filters.cursor.id)
        stmt = stmt.where(tuple_(WasteReportRow.created_at, WasteReportRow.id) < position)
    return stmt.order_by(WasteReportRow.created_at.desc(), WasteReportRow.id.desc()).limit(
        filters.limit + 1
    )


class SqlReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, new: NewReport) -> Report:
        row = WasteReportRow(
            tenant_id=new.tenant_id,
            location=func.ST_SetSRID(func.ST_MakePoint(new.longitude, new.latitude), 4326),
            accuracy_m=new.accuracy_m,
            location_source=new.location_source.value,
            amount_bucket=new.amount_bucket.value,
            waste_type=new.waste_type.value,
            description=new.description,
            reporter_id=new.reporter_id,
            reporter_role=new.reporter_role.value,
            observed_at=new.observed_at,
        )
        self._session.add(row)
        self._session.commit()
        report = self.get(row.id, new.tenant_id)
        assert report is not None  # just inserted
        return report

    def get(self, report_id: UUID, tenant_id: str | None) -> Report | None:
        stmt = _in_tenant(select(*_ROW_COLUMNS).where(WasteReportRow.id == report_id), tenant_id)
        found = self._session.execute(stmt).first()
        return _to_report(*found) if found else None

    def list(self, filters: ReportFilters, tenant_id: str | None) -> list[Report]:
        return [_to_report(*r) for r in self._session.execute(build_list_query(filters, tenant_id))]

    def update(
        self,
        report_id: UUID,
        tenant_id: str | None,
        expected_version: int,
        changes: dict[str, object],
    ) -> Report | None:
        values = {name: getattr(v, "value", v) for name, v in changes.items()}
        stmt = (
            update(WasteReportRow)
            .where(WasteReportRow.id == report_id, WasteReportRow.version == expected_version)
            .values(**values, version=WasteReportRow.version + 1, updated_at=func.now())
            .returning(WasteReportRow.id)
        )
        if tenant_id is not None:
            stmt = stmt.where(WasteReportRow.tenant_id == tenant_id)
        # One atomic UPDATE ... WHERE version = n: two concurrent writers can't both win
        updated = self._session.execute(stmt).first()
        self._session.commit()
        return self.get(report_id, tenant_id) if updated else None

    def ping(self) -> bool:
        try:
            self._session.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False


def get_repository(session: Annotated[Session, Depends(get_session)]) -> Iterator[ReportRepository]:
    yield SqlReportRepository(session)


Repository = Annotated[ReportRepository, Depends(get_repository)]
