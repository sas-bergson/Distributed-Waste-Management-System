"""Request and response bodies. Mirrors docs/api/locations.yaml."""

from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AmountBucket(StrEnum):
    """Palette Dimension A (README)."""

    EMPTY = "empty"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OVERFLOW = "overflow"


class WasteType(StrEnum):
    HOUSEHOLD = "household"
    PLASTIC = "plastic"
    ORGANIC = "organic"
    CONSTRUCTION = "construction"
    ELECTRONIC = "electronic"
    HAZARDOUS = "hazardous"
    MIXED = "mixed"
    OTHER = "other"


class LocationSource(StrEnum):
    GPS = "gps"
    MANUAL_PIN = "manual_pin"
    SENSOR = "sensor"  # only set by the IoT/device endpoint


class ReportStatus(StrEnum):
    OPEN = "open"
    COLLECTION_REQUESTED = "collection_requested"
    COLLECTED = "collected"
    INVALID = "invalid"


class Role(StrEnum):
    """User roles from ADR-0001."""

    CITIZEN = "citizen"
    FIELD_AGENT = "field_agent"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class ReporterRole(StrEnum):
    CITIZEN = "citizen"
    FIELD_AGENT = "field_agent"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    SENSOR = "sensor"


DESCRIPTION_MAX = 500


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float | None = Field(default=None, ge=0, le=10_000, allow_inf_nan=False)
    location_source: LocationSource = LocationSource.GPS
    amount_bucket: AmountBucket
    waste_type: WasteType
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    observed_at: datetime | None = None

    @field_validator("location_source")
    @classmethod
    def users_cannot_claim_sensor(cls, value: LocationSource) -> LocationSource:
        if value is LocationSource.SENSOR:
            raise ValueError("sensor readings go through the IoT endpoint; use gps or manual_pin")
        return value


class ReportUpdate(BaseModel):
    """Partial update: only the fields present in the body change."""

    model_config = ConfigDict(extra="forbid")

    amount_bucket: AmountBucket | None = None
    waste_type: WasteType | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    status: ReportStatus | None = None

    @model_validator(mode="after")
    def check_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("send at least one field to change")
        for name in ("amount_bucket", "waste_type", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self

    def changes(self) -> dict[str, object]:
        """Only the fields the client sent; `description: null` clears it."""
        return {name: getattr(self, name) for name in self.model_fields_set}


class Reporter(BaseModel):
    id: str
    role: ReporterRole


class Report(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    accuracy_m: float | None
    location_source: LocationSource
    amount_bucket: AmountBucket
    waste_type: WasteType
    description: str | None
    status: ReportStatus
    reporter: Reporter
    observed_at: datetime
    created_at: datetime
    updated_at: datetime
    version: int


class ReportPage(BaseModel):
    items: list[Report]
    next_cursor: str | None
