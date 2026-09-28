from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class DashboardSummary(BaseModel):
    total_entities: int
    entities_requiring_attention: int
    high_risk_findings: int
    execution_gaps_count: int
    negative_space_count: int
    anomalies_count: int
    total_alerts_ingested: int
    total_cases_ingested: int
    latest_run_id: Optional[str] = None
    latest_run_timestamp: Optional[datetime] = None


class EntitySupervisoryCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: str
    name: str
    sector: str
    claimed_tier: str
    monitored_asset_count: int
    active_reporting_assets: int
    coverage_gap_pct: float
    total_alerts: int
    total_cases: int
    execution_gaps_count: int
    negative_space_count: int
    anomalies_count: int
    risk_level: str  # LOW, MODERATE, HIGH, CRITICAL
    risk_score: float  # 0 to 100
    primary_concerns: List[str]


class ReviewItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: str
    finding_id: str
    entity_id: str
    assessment_period_id: Optional[str] = "2026-Q2"
    run_id: Optional[str] = None
    priority: str
    status: str
    assigned_reviewer: Optional[str] = None
    notes: Optional[str] = None
    finding_reason: Optional[str] = None
    finding_category: Optional[str] = None
    finding_severity: Optional[str] = None
    capability_dimension: Optional[str] = None
    recommended_review_area: Optional[str] = None
    updated_at: datetime


class ReviewActionRequest(BaseModel):
    status: str  # OPEN, UNDER_REVIEW, CONFIRMED, REJECTED, DEFERRED, REQUEST_EVIDENCE
    assigned_reviewer: Optional[str] = None
    notes: Optional[str] = None
    action_name: str = "STATUS_UPDATE"


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    action: str
    entity_id: Optional[str] = None
    actor: str
    details: Optional[Dict[str, Any]] = None
    previous_event_hash: Optional[str] = None
    event_hash: Optional[str] = None


from app.time_utils import utc_now


class AuditVerificationResult(BaseModel):
    verified: bool
    total_events: int
    tampered_events: List[int]
    root_hash: Optional[str] = None
    latest_hash: Optional[str] = None
    status: str
    verification_timestamp: datetime = Field(default_factory=utc_now)

