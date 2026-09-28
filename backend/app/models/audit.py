from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    action = Column(String, nullable=False, index=True)  # INGESTION, ANALYSIS_RUN, REVIEW_ACTION, REPORT_GENERATE, CONFIG_CHANGE
    entity_id = Column(String, nullable=True, index=True)
    actor = Column(String, default="SUPERVISOR")
    details_json = Column(Text, nullable=True)


class ReviewItem(Base):
    __tablename__ = "review_items"

    review_id = Column(String, primary_key=True, index=True)
    finding_id = Column(String, ForeignKey("findings.finding_id"), nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    priority = Column(String, default="HIGH")            # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String, default="OPEN")              # OPEN, UNDER_REVIEW, REVIEWED, DISMISSED, ESCALATED
    assigned_reviewer = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    actions_history_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
