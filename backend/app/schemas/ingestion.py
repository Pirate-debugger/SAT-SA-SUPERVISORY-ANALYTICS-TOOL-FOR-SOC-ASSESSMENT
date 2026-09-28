from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class IngestionValidationReport(BaseModel):
    batch_id: str
    filename: str
    file_type: str
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    missing_fields: List[str] = Field(default_factory=list)
    normalization_warnings: List[str] = Field(default_factory=list)
    invalid_samples: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "PENDING"  # SUCCESS, PARTIAL_SUCCESS, FAILED
    message: str = ""


class DetectedSchema(BaseModel):
    filename: str
    file_type: str
    total_rows_detected: int
    detected_data_category: str  # ALERT, CASE, ASSET, ENTITY
    columns_detected: List[str]
    suggested_mappings: Dict[str, str]
    confidence: float
    warnings: List[str] = Field(default_factory=list)


class CustomMappingRequest(BaseModel):
    batch_id: str
    column_mapping: Dict[str, str]
    data_category: str  # ALERT or CASE
    default_entity_id: Optional[str] = None
