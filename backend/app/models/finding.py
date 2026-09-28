from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base
from app.time_utils import utc_now


class Finding(Base):
    __tablename__ = "findings"

    finding_id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("analysis_runs.run_id"), nullable=False, index=True)
    entity_id = Column(String, ForeignKey("entities.entity_id"), nullable=False, index=True)
    assessment_period_id = Column(String, default="2026-Q2", index=True)
    dataset_version_id = Column(String, default="v1.0", index=True)
    finding_type = Column(String, nullable=False, index=True)  # RAPID_CLOSURE_CRITICAL, NEGATIVE_SPACE_ASSET_SILENCE, etc.
    capability_dimension = Column(String, default="SECURITY_OPERATIONS", index=True)  # 1 of 8 dimensions
    category = Column(String, nullable=False, index=True)      # EXECUTION_GAP, NEGATIVE_SPACE, ANOMALY
    severity = Column(String, nullable=False, index=True)      # CRITICAL, HIGH, MEDIUM, LOW
    confidence = Column(Float, default=0.9)                    # 0.0 - 1.0
    rule_id = Column(String, nullable=True, index=True)        # e.g., "RULE-GAP-01", "RULE-NEG-01"
    reason = Column(Text, nullable=False)                      # Plain English explanation
    evidence_summary = Column(Text, nullable=False)            # Readable summary of evidence
    observed_value_json = Column(Text, nullable=True)          # Explicit observed metric
    expected_value_json = Column(Text, nullable=True)          # Explicit expectation / norm
    metric_values_json = Column(Text, nullable=True)           # Detailed metrics dictionary
    baseline_json = Column(Text, nullable=True)                # Thresholds or peer baseline
    recommended_review_area = Column(Text, nullable=True)      # Actionable supervisory guidance
    nist_csf_category = Column(String, nullable=True)          # Optional NIST CSF 2.0 mapping (e.g., DE.CM, RS.RP)
    mitre_attack_technique = Column(String, nullable=True)     # Optional ATT&CK technique reference
    sample_size = Column(Integer, default=0)
    status = Column(String, default="OPEN")                    # OPEN, UNDER_REVIEW, CONFIRMED, REJECTED, DEFERRED, REQUEST_EVIDENCE
    created_at = Column(DateTime(timezone=True), default=utc_now)

    run = relationship("AnalysisRun", back_populates="findings")
    evidence_links = relationship("FindingEvidenceLink", back_populates="finding", cascade="all, delete-orphan")

    @property
    def analysis_run_id(self) -> str:
        return self.run_id

    __table_args__ = (
        Index("ix_findings_run_entity", "run_id", "entity_id"),
        Index("ix_findings_entity_period", "entity_id", "assessment_period_id"),
    )


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
