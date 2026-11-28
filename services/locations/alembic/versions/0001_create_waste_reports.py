"""Create locations.waste_reports (the minimal table Feature 18 needs).

Feature 21 (PostGIS schema & seeding) owns the full schema and seed data; it builds on top of
this table instead of creating its own.

Revision ID: 0001
Revises:
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "locations"


def _one_of(column: str, values: list[str]) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=f"ck_waste_reports_{column}")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    op.create_table(
        "waste_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("location_source", sa.String(20), nullable=False),
        sa.Column("amount_bucket", sa.String(20), nullable=False),
        sa.Column("waste_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'open'")),
        sa.Column("reporter_id", sa.String(100), nullable=False),
        sa.Column("reporter_role", sa.String(20), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        _one_of("location_source", ["gps", "manual_pin", "sensor"]),
        _one_of("amount_bucket", ["empty", "low", "moderate", "high", "overflow"]),
        _one_of(
            "waste_type",
            [
                "household",
                "plastic",
                "organic",
                "construction",
                "electronic",
                "hazardous",
                "mixed",
                "other",
            ],
        ),
        _one_of("status", ["open", "collection_requested", "collected", "invalid"]),
        _one_of("reporter_role", ["citizen", "field_agent", "supervisor", "admin", "sensor"]),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_waste_reports_location",
        "waste_reports",
        ["location"],
        schema=SCHEMA,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_waste_reports_tenant_created",
        "waste_reports",
        ["tenant_id", "created_at", "id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_waste_reports_tenant_updated",
        "waste_reports",
        ["tenant_id", "updated_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("waste_reports", schema=SCHEMA)  # also drops its indexes
