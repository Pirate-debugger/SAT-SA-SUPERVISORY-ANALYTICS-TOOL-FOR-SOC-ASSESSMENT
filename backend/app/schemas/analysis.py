from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class FindingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: str
    run_id: str
    entity_id: str
    finding_type: str
    category: str  # EXECUTION_GAP, NEGATIVE_SPACE, ANOMALY
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    confidence: float
    reason: str
    evidence_summary: str
    metric_values: Optional[Dict[str, Any]] = None
    baseline: Optional[Dict[str, Any]] = None
    sample_size: int = 0
    status: str = "NEW"
    created_at: datetime


class FindingEvidenceLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_type: str
    record_id: str
    relevance_note: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class FindingDetailOut(FindingBase):
    evidence_records: List[FindingEvidenceLinkOut] = Field(default_factory=list)


class AnalysisRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    timestamp: datetime
    dataset_version: str
    ruleset_version: str
    analytics_version: str
    status: str
    entities_analyzed_count: int
    alerts_analyzed_count: int
    cases_analyzed_count: int
    findings_count: int
    summary: Optional[Dict[str, Any]] = None
    execution_time_seconds: float


class RunAnalysisRequest(BaseModel):
    entity_ids: Optional[List[str]] = None
    dataset_version: Optional[str] = "v1.0-offline"
    note: Optional[str] = "Supervisory SOC periodic assessment run"
