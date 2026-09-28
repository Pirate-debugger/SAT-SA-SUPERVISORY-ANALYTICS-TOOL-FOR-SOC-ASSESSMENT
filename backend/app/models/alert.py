from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String, ForeignKey("entities.entity_id"), nullable=False, index=True)
    alert_id = Column(String, nullable=False, index=True)
    alert_timestamp = Column(DateTime, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    category = Column(String, nullable=False, index=True)  # RANSOMWARE, BRUTE_FORCE, etc.
    source_system = Column(String, nullable=True)
    asset_id = Column(String, nullable=True, index=True)
    acknowledged_timestamp = Column(DateTime, nullable=True)
    investigation_started_timestamp = Column(DateTime, nullable=True)
    closed_timestamp = Column(DateTime, nullable=True)
    disposition = Column(String, nullable=True)            # TRUE_POSITIVE, FALSE_POSITIVE, BENIGN, UNKNOWN
    escalated = Column(Boolean, nullable=True)
    escalation_timestamp = Column(DateTime, nullable=True)
    investigator_id = Column(String, nullable=True)
    root_cause_recorded = Column(Boolean, default=False)
    remediation_recorded = Column(Boolean, default=False)
    evidence_present = Column(Boolean, default=False)
    status = Column(String, default="CLOSED")              # OPEN, CLOSED, IN_PROGRESS, ESCALATED
    ingestion_batch_id = Column(String, nullable=True, index=True)
    raw_data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_entity_timestamp", "entity_id", "alert_timestamp"),
        Index("ix_alerts_entity_severity", "entity_id", "severity"),
    )
