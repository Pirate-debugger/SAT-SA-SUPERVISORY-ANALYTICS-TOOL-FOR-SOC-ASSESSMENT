from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String, ForeignKey("entities.entity_id"), nullable=False, index=True)
    case_id = Column(String, nullable=False, index=True)
    assessment_period_id = Column(String, default="2026-Q2", index=True)
    alert_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=True)
    investigation_started_at = Column(DateTime, nullable=True)
    escalation_status = Column(String, nullable=True)     # NOT_ESCALATED, ESCALATED_TIER2, ESCALATED_LEAD, etc.
    escalation_timestamp = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    disposition = Column(String, nullable=True)           # TRUE_POSITIVE, FALSE_POSITIVE, BENIGN, RESOLVED, UNKNOWN
    root_cause = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    investigator = Column(String, nullable=True)
    closure_reason = Column(Text, nullable=True)
    ingestion_batch_id = Column(String, nullable=True, index=True)
    provenance_id = Column(String, nullable=True, index=True)

    entity = relationship("Entity", back_populates="cases")

    __table_args__ = (
        Index("ix_cases_entity_created", "entity_id", "created_at"),
        Index("ix_cases_entity_period", "entity_id", "assessment_period_id"),
    )
