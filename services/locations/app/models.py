import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings
from app.schemas import AmountBucket, LocationSource, ReporterRole, ReportStatus, WasteType


def _one_of(column: str, values: type[Any]) -> CheckConstraint:
    allowed = ", ".join(f"'{v.value}'" for v in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=f"ck_waste_reports_{column}")


class Base(DeclarativeBase):
    metadata = MetaData(schema=get_settings().db_schema)


class WasteReportRow(Base):
    __tablename__ = "waste_reports"
    __table_args__ = (
        _one_of("location_source", LocationSource),
        _one_of("amount_bucket", AmountBucket),
        _one_of("waste_type", WasteType),
        _one_of("status", ReportStatus),
        _one_of("reporter_role", ReporterRole),
        # Viewport / bbox queries (CONTRIBUTING.md: spatial queries must use a GiST index)
        Index("ix_waste_reports_location", "location", postgresql_using="gist"),
        # Newest-first listing per district, and incremental sync
        Index("ix_waste_reports_tenant_created", "tenant_id", "created_at", "id"),
        Index("ix_waste_reports_tenant_updated", "tenant_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100))
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False))
    accuracy_m: Mapped[float | None] = mapped_column(Float)
    location_source: Mapped[str] = mapped_column(String(20))
    amount_bucket: Mapped[str] = mapped_column(String(20))
    waste_type: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), server_default=text("'open'"))
    reporter_id: Mapped[str] = mapped_column(String(100))
    reporter_role: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Set by the database clock, so every replica agrees on the order of events
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
