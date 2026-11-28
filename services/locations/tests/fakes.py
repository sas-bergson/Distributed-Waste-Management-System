"""In-memory ReportRepository with the same rules as the PostGIS one, for fast tests."""

import itertools
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repository import NewReport, ReportFilters
from app.schemas import Report, Reporter, ReportStatus


class InMemoryReportRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, tuple[str, Report]] = {}  # id -> (tenant_id, report)
        self.database_up = True
        # Strictly increasing timestamps, like distinct inserts in the database
        self._clock = (
            datetime(2026, 11, 1, tzinfo=UTC) + timedelta(seconds=i) for i in itertools.count()
        )

    def create(self, new: NewReport) -> Report:
        now = next(self._clock)
        report = Report(
            id=uuid.uuid4(),
            latitude=new.latitude,
            longitude=new.longitude,
            accuracy_m=new.accuracy_m,
            location_source=new.location_source,
            amount_bucket=new.amount_bucket,
            waste_type=new.waste_type,
            description=new.description,
            status=ReportStatus.OPEN,
            reporter=Reporter(id=new.reporter_id, role=new.reporter_role),
            observed_at=new.observed_at,
            created_at=now,
            updated_at=now,
            version=1,
        )
        self.rows[report.id] = (new.tenant_id, report)
        return report

    def get(self, report_id: UUID, tenant_id: str | None) -> Report | None:
        found = self.rows.get(report_id)
        if found is None or (tenant_id is not None and found[0] != tenant_id):
            return None
        return found[1]

    def list(self, filters: ReportFilters, tenant_id: str | None) -> list[Report]:
        def keep(tenant: str, r: Report) -> bool:
            b = filters.bbox
            return (
                (tenant_id is None or tenant == tenant_id)
                and (
                    b is None
                    or (
                        b.lat_min <= r.latitude <= b.lat_max
                        and b.lon_min <= r.longitude <= b.lon_max
                    )
                )
                and (not filters.amount_buckets or r.amount_bucket in filters.amount_buckets)
                and (not filters.waste_types or r.waste_type in filters.waste_types)
                and (not filters.statuses or r.status in filters.statuses)
                and (filters.updated_since is None or r.updated_at > filters.updated_since)
                and (
                    filters.cursor is None
                    or (r.created_at, r.id) < (filters.cursor.created_at, filters.cursor.id)
                )
            )

        matches = [r for tenant, r in self.rows.values() if keep(tenant, r)]
        matches.sort(key=lambda r: (r.created_at, r.id), reverse=True)
        return matches[: filters.limit + 1]

    def update(
        self,
        report_id: UUID,
        tenant_id: str | None,
        expected_version: int,
        changes: dict[str, object],
    ) -> Report | None:
        current = self.get(report_id, tenant_id)
        if current is None or current.version != expected_version:
            return None
        updated = current.model_copy(
            update={**changes, "version": current.version + 1, "updated_at": next(self._clock)}
        )
        self.rows[report_id] = (self.rows[report_id][0], updated)
        return updated

    def ping(self) -> bool:
        return self.database_up
