from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Finding(Base):
    __tablename__ = "findings"

    finding_id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("analysis_runs.run_id"), nullable=False, index=True)
    entity_id = Column(String, ForeignKey("entities.entity_id"), nullable=False, index=True)
    finding_type = Column(String, nullable=False, index=True)  # RAPID_CLOSURE_CRITICAL, NEGATIVE_SPACE_ASSET_SILENCE, etc.
    category = Column(String, nullable=False, index=True)      # EXECUTION_GAP, NEGATIVE_SPACE, ANOMALY
    severity = Column(String, nullable=False, index=True)      # CRITICAL, HIGH, MEDIUM, LOW
    confidence = Column(Float, default=0.9)                    # 0.0 - 1.0
    reason = Column(Text, nullable=False)                      # Plain English reason
    evidence_summary = Column(Text, nullable=False)            # Readable summary of evidence
    metric_values_json = Column(Text, nullable=True)           # JSON string of observed values
    baseline_json = Column(Text, nullable=True)                # JSON string of thresholds/peer baseline
    sample_size = Column(Integer, default=0)
    status = Column(String, default="NEW")                     # NEW, UNDER_REVIEW, VERIFIED, DISMISSED
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("AnalysisRun", back_populates="findings")
    evidence_links = relationship("FindingEvidenceLink", back_populates="finding", cascade="all, delete-orphan")


class FindingEvidenceLink(Base):
    __tablename__ = "finding_evidence_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    finding_id = Column(String, ForeignKey("findings.finding_id"), nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    record_type = Column(String, nullable=False)               # ALERT, CASE, ASSET
    record_id = Column(String, nullable=False, index=True)     # alert_id, case_id, asset_id
    relevance_note = Column(Text, nullable=True)

    finding = relationship("Finding", back_populates="evidence_links")

    __table_args__ = (
        Index("ix_evidence_finding_record", "finding_id", "record_id"),
    )
