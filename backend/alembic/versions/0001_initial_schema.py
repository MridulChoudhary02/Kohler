"""Initial schema — all tables matching PRD Section 6 ER diagram exactly

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-15 14:04:00

Tables created (in dependency order):
  facilities, technicians, zones, sla_policies, fixtures,
  sensors, telemetry_readings, baseline_profiles,
  detection_events, tickets, hygiene_counters
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── FACILITIES ────────────────────────────────────────────────
    op.create_table(
        "facilities",
        sa.Column("facility_id", sa.String(36), primary_key=True),
        sa.Column("name",        sa.String(255), nullable=False),
        sa.Column("type",        sa.String(100), nullable=False),
    )

    # ── TECHNICIANS (no FK dependencies) ──────────────────────────
    op.create_table(
        "technicians",
        sa.Column("tech_id", sa.String(36), primary_key=True),
        sa.Column("name",    sa.String(255), nullable=False),
        sa.Column("team",    sa.String(100), nullable=False),
    )

    # ── ZONES ─────────────────────────────────────────────────────
    op.create_table(
        "zones",
        sa.Column("zone_id",             sa.String(36),  primary_key=True),
        sa.Column("facility_id",         sa.String(36),  sa.ForeignKey("facilities.facility_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",                sa.String(255), nullable=False),
        sa.Column("criticality_tier",    sa.String(50),  nullable=False),
        sa.Column("occupancy_sensor_id", sa.String(36),  nullable=True),
    )
    op.create_index("ix_zones_facility_id",      "zones", ["facility_id"])
    op.create_index("ix_zones_criticality_tier", "zones", ["criticality_tier"])

    # ── SLA_POLICIES ──────────────────────────────────────────────
    op.create_table(
        "sla_policies",
        sa.Column("zone_id",          sa.String(36), sa.ForeignKey("zones.zone_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("criticality_tier", sa.String(50), nullable=False),
        sa.Column("response_minutes", sa.Integer,    nullable=False),
    )

    # ── FIXTURES ──────────────────────────────────────────────────
    op.create_table(
        "fixtures",
        sa.Column("fixture_id",   sa.String(36),  primary_key=True),
        sa.Column("zone_id",      sa.String(36),  sa.ForeignKey("zones.zone_id", ondelete="CASCADE"), nullable=False),
        sa.Column("fixture_type", sa.String(100), nullable=False),
        sa.Column("install_date", sa.String(20),  nullable=False),
    )
    op.create_index("ix_fixtures_zone_id",      "fixtures", ["zone_id"])
    op.create_index("ix_fixtures_fixture_type", "fixtures", ["fixture_type"])

    # ── SENSORS ───────────────────────────────────────────────────
    op.create_table(
        "sensors",
        sa.Column("sensor_id",   sa.String(36),  primary_key=True),
        sa.Column("fixture_id",  sa.String(36),  sa.ForeignKey("fixtures.fixture_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("sensor_type", sa.String(100), nullable=False),
        sa.Column("status",      sa.String(50),  nullable=False, server_default="active"),
    )

    # ── TELEMETRY_READINGS ────────────────────────────────────────
    op.create_table(
        "telemetry_readings",
        sa.Column("reading_id",        sa.String(36),  primary_key=True),
        sa.Column("sensor_id",         sa.String(36),  sa.ForeignKey("sensors.sensor_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp",         sa.DateTime(timezone=True), nullable=False),
        sa.Column("flow_rate_lpm",     sa.Float,       nullable=False),
        sa.Column("flush_event",       sa.Integer,     nullable=False, server_default="0"),
        sa.Column("occupancy_state",   sa.Integer,     nullable=False, server_default="0"),
        sa.Column("diagnostic_status", sa.String(50),  nullable=False, server_default="ok"),
    )
    op.create_index("ix_telemetry_sensor_ts", "telemetry_readings", ["sensor_id", "timestamp"])
    op.create_index("ix_telemetry_timestamp", "telemetry_readings", ["timestamp"])

    # ── BASELINE_PROFILES ─────────────────────────────────────────
    op.create_table(
        "baseline_profiles",
        sa.Column("fixture_id",            sa.String(36), sa.ForeignKey("fixtures.fixture_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mean_off_flow",         sa.Float,      nullable=False, server_default="0.0"),
        sa.Column("std_off_flow",          sa.Float,      nullable=False, server_default="0.05"),
        sa.Column("mean_flush_volume",     sa.Float,      nullable=False, server_default="6.0"),
        sa.Column("mean_flush_duration_s", sa.Float,      nullable=False, server_default="10.0"),
        sa.Column("last_updated",          sa.DateTime(timezone=True), nullable=False),
    )

    # ── DETECTION_EVENTS ──────────────────────────────────────────
    op.create_table(
        "detection_events",
        sa.Column("event_id",         sa.String(36), primary_key=True),
        sa.Column("fixture_id",       sa.String(36), sa.ForeignKey("fixtures.fixture_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type",       sa.String(50), nullable=False),
        sa.Column("confidence_score", sa.Float,      nullable=False),
        sa.Column("evidence_value",   sa.Float,      nullable=True),
        sa.Column("detected_at",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("status",           sa.String(50), nullable=False, server_default="logged"),
    )
    op.create_index("ix_detection_events_fixture_id",  "detection_events", ["fixture_id"])
    op.create_index("ix_detection_events_detected_at", "detection_events", ["detected_at"])
    op.create_index("ix_detection_events_status",      "detection_events", ["status"])

    # ── TICKETS ───────────────────────────────────────────────────
    op.create_table(
        "tickets",
        sa.Column("ticket_id",       sa.String(36), primary_key=True),
        sa.Column("event_id",        sa.String(36), sa.ForeignKey("detection_events.event_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("zone_id",         sa.String(36), sa.ForeignKey("zones.zone_id"), nullable=False),
        sa.Column("priority_score",  sa.Float,      nullable=False),
        sa.Column("status",          sa.String(50), nullable=False, server_default="open"),
        sa.Column("sla_due",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_team",   sa.String(100), nullable=True),
        sa.Column("assigned_tech_id",sa.String(36), sa.ForeignKey("technicians.tech_id"), nullable=True),
        sa.Column("summary_text",    sa.Text,        nullable=True),
    )
    op.create_index("ix_tickets_status",         "tickets", ["status"])
    op.create_index("ix_tickets_zone_id",        "tickets", ["zone_id"])
    op.create_index("ix_tickets_priority_score", "tickets", ["priority_score"])

    # ── HYGIENE_COUNTERS ──────────────────────────────────────────
    op.create_table(
        "hygiene_counters",
        sa.Column("id",                    sa.String(36), primary_key=True),
        sa.Column("fixture_id",            sa.String(36), sa.ForeignKey("fixtures.fixture_id", ondelete="CASCADE"), nullable=False),
        sa.Column("uses_since_clean",      sa.Integer,    nullable=False, server_default="0"),
        sa.Column("last_cleaned",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("predicted_breach_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hygiene_counters_fixture_id", "hygiene_counters", ["fixture_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("hygiene_counters")
    op.drop_table("tickets")
    op.drop_table("detection_events")
    op.drop_table("baseline_profiles")
    op.drop_table("telemetry_readings")
    op.drop_table("sensors")
    op.drop_table("fixtures")
    op.drop_table("sla_policies")
    op.drop_table("zones")
    op.drop_table("technicians")
    op.drop_table("facilities")
