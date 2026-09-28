from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.database import Base


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    batch_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # CSV, JSON, SQLITE
    entity_id = Column(String, nullable=True, index=True)
    status = Column(String, default="PENDING")   # SUCCESS, PARTIAL_SUCCESS, FAILED
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    invalid_records = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    missing_fields_json = Column(Text, nullable=True)
    normalization_warnings_json = Column(Text, nullable=True)
    invalid_records_sample_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
