"""
SQLAlchemy models — exact implementation of Section 6 ER diagram.
Field names and relationships follow the PRD entity/field names verbatim.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, Index
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


def new_uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# FACILITY
# ─────────────────────────────────────────────
class Facility(Base):
    __tablename__ = "facilities"

    facility_id  = Column(String(36), primary_key=True, default=new_uuid)
    name         = Column(String(255), nullable=False)
    type         = Column(String(100), nullable=False)  # e.g. "Hospital"

    zones = relationship("Zone", back_populates="facility")


# ─────────────────────────────────────────────
# ZONE
# ─────────────────────────────────────────────
class Zone(Base):
    __tablename__ = "zones"

    zone_id              = Column(String(36), primary_key=True, default=new_uuid)
    facility_id          = Column(String(36), ForeignKey("facilities.facility_id"), nullable=False)
    name                 = Column(String(255), nullable=False)
    criticality_tier     = Column(String(50), nullable=False)   # "Tier 1", "Tier 2", "Tier 3", "Tier 4"
    occupancy_sensor_id  = Column(String(36), nullable=True)    # FK resolved at runtime (nullable, circular)

    facility    = relationship("Facility", back_populates="zones")
    fixtures    = relationship("Fixture", back_populates="zone")
    sla_policy  = relationship("SLAPolicy", back_populates="zone", uselist=False)

    __table_args__ = (
        Index("ix_zones_facility_id", "facility_id"),
        Index("ix_zones_criticality_tier", "criticality_tier"),
    )


# ─────────────────────────────────────────────
# FIXTURE
# ─────────────────────────────────────────────
class Fixture(Base):
    __tablename__ = "fixtures"

    fixture_id    = Column(String(36), primary_key=True, default=new_uuid)
    zone_id       = Column(String(36), ForeignKey("zones.zone_id"), nullable=False)
    fixture_type  = Column(String(100), nullable=False)   # faucet | flush_valve | urinal | shower | scrub_tap
    install_date  = Column(String(20), nullable=False)    # ISO date string, per PRD "string" type

    zone             = relationship("Zone", back_populates="fixtures")
    sensor           = relationship("Sensor", back_populates="fixture", uselist=False)
    baseline_profile = relationship("BaselineProfile", back_populates="fixture", uselist=False)
    detection_events = relationship("DetectionEvent", back_populates="fixture")
    hygiene_counters = relationship("HygieneCounter", back_populates="fixture")

    __table_args__ = (
        Index("ix_fixtures_zone_id", "zone_id"),
        Index("ix_fixtures_fixture_type", "fixture_type"),
    )


# ─────────────────────────────────────────────
# SENSOR
# ─────────────────────────────────────────────
class Sensor(Base):
    __tablename__ = "sensors"

    sensor_id    = Column(String(36), primary_key=True, default=new_uuid)
    fixture_id   = Column(String(36), ForeignKey("fixtures.fixture_id"), nullable=False, unique=True)
    sensor_type  = Column(String(100), nullable=False)   # e.g. "flow_occupancy_combined"
    status       = Column(String(50), nullable=False, default="active")  # active | degraded | offline

    fixture          = relationship("Fixture", back_populates="sensor")
    telemetry_readings = relationship("TelemetryReading", back_populates="sensor")


# ─────────────────────────────────────────────
# TELEMETRY_READING
# ─────────────────────────────────────────────
class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    reading_id        = Column(String(36), primary_key=True, default=new_uuid)
    sensor_id         = Column(String(36), ForeignKey("sensors.sensor_id"), nullable=False)
    timestamp         = Column(DateTime(timezone=True), nullable=False, index=True)
    flow_rate_lpm     = Column(Float, nullable=False)
    flush_event       = Column(Integer, nullable=False, default=0)   # 0 or 1
    occupancy_state   = Column(Integer, nullable=False, default=0)   # 0 or 1
    diagnostic_status = Column(String(50), nullable=False, default="ok")  # ok | missing | out_of_range | flatline

    sensor = relationship("Sensor", back_populates="telemetry_readings")

    __table_args__ = (
        Index("ix_telemetry_sensor_ts", "sensor_id", "timestamp"),
    )


# ─────────────────────────────────────────────
# BASELINE_PROFILE
# ─────────────────────────────────────────────
class BaselineProfile(Base):
    __tablename__ = "baseline_profiles"

    fixture_id             = Column(String(36), ForeignKey("fixtures.fixture_id"), primary_key=True)
    mean_off_flow          = Column(Float, nullable=False, default=0.0)
    std_off_flow           = Column(Float, nullable=False, default=0.05)
    mean_flush_volume      = Column(Float, nullable=False, default=6.0)   # litres
    mean_flush_duration_s  = Column(Float, nullable=False, default=10.0)  # seconds
    last_updated           = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # ── Warm-up state (PRD Section 7.5) ────────────────────────────────────────
    # False = baseline is an untrusted placeholder; detection events are logged
    # only, never auto-dispatched, until warmup_complete flips to True.
    # The detection engine (Phase 2) sets this to True after BASELINE_WARMUP_DAYS
    # of real telemetry has accumulated.
    warmup_complete    = Column(Boolean, nullable=False, default=False)
    warmup_started_at  = Column(DateTime(timezone=True), nullable=True)

    fixture = relationship("Fixture", back_populates="baseline_profile")



# ─────────────────────────────────────────────
# DETECTION_EVENT
# ─────────────────────────────────────────────
class DetectionEvent(Base):
    __tablename__ = "detection_events"

    event_id        = Column(String(36), primary_key=True, default=new_uuid)
    fixture_id      = Column(String(36), ForeignKey("fixtures.fixture_id"), nullable=False)
    event_type      = Column(String(50), nullable=False)   # leak | hygiene | sensor_fault
    confidence_score = Column(Float, nullable=False)
    evidence_value  = Column(Float, nullable=True)          # litres/hr estimated waste, or predicted breach minutes
    detected_at     = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status          = Column(String(50), nullable=False, default="logged")  # logged | dispatched | resolved

    fixture = relationship("Fixture", back_populates="detection_events")
    ticket  = relationship("Ticket", back_populates="event", uselist=False)

    __table_args__ = (
        Index("ix_detection_events_fixture_id", "fixture_id"),
        Index("ix_detection_events_detected_at", "detected_at"),
        Index("ix_detection_events_status", "status"),
    )


# ─────────────────────────────────────────────
# TICKET
# ─────────────────────────────────────────────
class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id      = Column(String(36), primary_key=True, default=new_uuid)
    event_id       = Column(String(36), ForeignKey("detection_events.event_id"), nullable=False, unique=True)
    zone_id        = Column(String(36), ForeignKey("zones.zone_id"), nullable=False)
    priority_score = Column(Float, nullable=False)
    status         = Column(String(50), nullable=False, default="open")  # open | acknowledged | in_progress | resolved
    sla_due        = Column(DateTime(timezone=True), nullable=True)
    assigned_team  = Column(String(100), nullable=True)

    # PRD: TICKET }o--|| TECHNICIAN (optional many-to-one assignment)
    assigned_tech_id = Column(String(36), ForeignKey("technicians.tech_id"), nullable=True)

    # LLM-generated summary (added in Phase 7, nullable until then)
    summary_text   = Column(Text, nullable=True)

    event      = relationship("DetectionEvent", back_populates="ticket")
    zone       = relationship("Zone")
    technician = relationship("Technician", back_populates="tickets")

    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_zone_id", "zone_id"),
        Index("ix_tickets_priority_score", "priority_score"),
    )


# ─────────────────────────────────────────────
# TECHNICIAN
# ─────────────────────────────────────────────
class Technician(Base):
    __tablename__ = "technicians"

    tech_id = Column(String(36), primary_key=True, default=new_uuid)
    name    = Column(String(255), nullable=False)
    team    = Column(String(100), nullable=False)   # e.g. "Critical Care Maintenance", "Plumbing"

    tickets = relationship("Ticket", back_populates="technician")


# ─────────────────────────────────────────────
# SLA_POLICY
# ─────────────────────────────────────────────
class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    zone_id           = Column(String(36), ForeignKey("zones.zone_id"), primary_key=True)
    criticality_tier  = Column(String(50), nullable=False)
    response_minutes  = Column(Integer, nullable=False)  # 15 | 30 | 60 | 120

    zone = relationship("Zone", back_populates="sla_policy")


# ─────────────────────────────────────────────
# HYGIENE_COUNTER
# ─────────────────────────────────────────────
class HygieneCounter(Base):
    __tablename__ = "hygiene_counters"

    # Composite PK: one active counter per fixture (use fixture_id as PK since PRD says 1:many but one is "current")
    # The PRD shows FIXTURE ||--o{ HYGIENE_COUNTER — tracking history over cleaning cycles
    id                    = Column(String(36), primary_key=True, default=new_uuid)
    fixture_id            = Column(String(36), ForeignKey("fixtures.fixture_id"), nullable=False)
    uses_since_clean      = Column(Integer, nullable=False, default=0)
    last_cleaned          = Column(DateTime(timezone=True), nullable=True)
    predicted_breach_time = Column(DateTime(timezone=True), nullable=True)

    fixture = relationship("Fixture", back_populates="hygiene_counters")

    __table_args__ = (
        Index("ix_hygiene_counters_fixture_id", "fixture_id"),
    )
