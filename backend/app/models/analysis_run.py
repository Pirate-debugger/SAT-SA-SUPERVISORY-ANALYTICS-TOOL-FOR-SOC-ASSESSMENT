from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base
from app.time_utils import utc_now


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    run_id = Column(String, primary_key=True, index=True)
    assessment_period_id = Column(String, default="2026-Q2", index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, index=True)
    started_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    dataset_version = Column(String, default="v1.0")
    ruleset_version = Column(String, default="ruleset-v1.2.0-authoritative")
    analytics_version = Column(String, default="analytics-v1.2.0-offline")
    model_version = Column(String, default="iso-forest-v1.2.0-adaptive")
    config_hash = Column(String, nullable=True, index=True)
    is_latest = Column(Boolean, default=True, index=True)  # Key for run isolation!
    status = Column(String, default="PENDING")             # PENDING, RUNNING, COMPLETED, FAILED
    entities_analyzed_count = Column(Integer, default=0)
    alerts_analyzed_count = Column(Integer, default=0)
    cases_analyzed_count = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    summary_json = Column(Text, nullable=True)
    execution_time_seconds = Column(Float, default=0.0)

    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")
    capability_scores = relationship("CapabilityScore", back_populates="run", cascade="all, delete-orphan")

    @property
    def analysis_run_id(self) -> str:
        return self.run_id


class CapabilityScore(Base):
    __tablename__ = "capability_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("analysis_runs.run_id"), nullable=False, index=True)
    entity_id = Column(String, ForeignKey("entities.entity_id"), nullable=False, index=True)
    assessment_period_id = Column(String, default="2026-Q2", index=True)
    dimension = Column(String, nullable=False, index=True)  # e.g. THREAT_DETECTION, INVESTIGATION, ESCALATION, etc.
    score = Column(Float, default=70.0)                     # 0 - 100
    status = Column(String, default="ADEQUATE")             # STRONG EVIDENCE, ATTENTION, INSUFFICIENT EVIDENCE, NOT ASSESSED
    observed_metrics_json = Column(Text, nullable=True)
    baseline_json = Column(Text, nullable=True)
    peer_median = Column(Float, default=70.0)
    deviation = Column(Float, default=0.0)
    confidence = Column(Float, default=0.90)
    trend = Column(String, default="STABLE")                # IMPROVING, STABLE, DETERIORATING
    created_at = Column(DateTime(timezone=True), default=utc_now)

    run = relationship("AnalysisRun", back_populates="capability_scores")

    __table_args__ = (
        Index("ix_capability_run_entity_dim", "run_id", "entity_id", "dimension"),
    )
