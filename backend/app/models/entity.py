from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.database import Base


class AssessmentPeriod(Base):
    __tablename__ = "assessment_periods"

    period_id = Column(String, primary_key=True, index=True)  # e.g., "2026-Q2", "2026-Q1", "2025-Q4"
    name = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatasetProvenance(Base):
    __tablename__ = "dataset_provenances"

    provenance_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)  # SHA-256
    source_name = Column(String, nullable=False)
    assessment_period_id = Column(String, ForeignKey("assessment_periods.period_id"), nullable=True, index=True)
    record_count = Column(Integer, default=0)
    data_quality_pct = Column(Float, default=100.0)
    unknown_fields_summary_json = Column(Text, nullable=True)
    schema_version = Column(String, default="v1.0-canonical")
    mapping_version = Column(String, default="v1.0-auto")
    import_timestamp = Column(DateTime, default=datetime.utcnow)


class Entity(Base):
    __tablename__ = "entities"

    entity_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    claimed_tier = Column(String, default="Tier-1 Critical Sector Entity")
    monitored_asset_count = Column(Integer, default=0)
    soc_model = Column(String, default="In-house 24/7 SOC")
    contact_email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assets = relationship("Asset", back_populates="entity", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="entity", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="entity", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(String, primary_key=True, index=True)
    entity_id = Column(String, ForeignKey("entities.entity_id"), nullable=False, index=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    criticality = Column(String, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    asset_type = Column(String, nullable=False)   # SCADA, CORE_ROUTER, PAYMENT_GW, etc.
    expected_monitoring = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="assets")
