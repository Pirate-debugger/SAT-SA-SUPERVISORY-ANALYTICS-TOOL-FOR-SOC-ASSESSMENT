from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    run_id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    dataset_version = Column(String, default="v1.0")
    ruleset_version = Column(String, default="ruleset-v1.0.0-offline")
    analytics_version = Column(String, default="analytics-v1.0.0-baseline")
    status = Column(String, default="PENDING")   # PENDING, RUNNING, COMPLETED, FAILED
    entities_analyzed_count = Column(Integer, default=0)
    alerts_analyzed_count = Column(Integer, default=0)
    cases_analyzed_count = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    summary_json = Column(Text, nullable=True)
    execution_time_seconds = Column(Float, default=0.0)

    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")
