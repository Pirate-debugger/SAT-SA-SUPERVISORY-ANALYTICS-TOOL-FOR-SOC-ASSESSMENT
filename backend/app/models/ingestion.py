from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from app.database import Base
from app.time_utils import utc_now


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    batch_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # CSV, JSON, SQLITE
    file_hash = Column(String, nullable=True, index=True)  # SHA-256
    entity_id = Column(String, nullable=True, index=True)
    assessment_period_id = Column(String, default="2026-Q2", index=True)
    status = Column(String, default="PENDING")   # SUCCESS, PARTIAL_SUCCESS, FAILED
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    invalid_records = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    data_quality_pct = Column(Float, default=100.0)
    unknown_values_count = Column(Integer, default=0)
    missing_fields_json = Column(Text, nullable=True)
    normalization_warnings_json = Column(Text, nullable=True)
    invalid_records_sample_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
