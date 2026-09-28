from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class EntityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: str
    name: str
    sector: str
    claimed_tier: str = "Tier-1 Critical Sector Entity"
    monitored_asset_count: int = 0
    soc_model: str = "In-house 24/7 SOC"
    contact_email: Optional[str] = None
    is_active: bool = True


class AssetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    entity_id: str
    hostname: str
    ip_address: Optional[str] = None
    criticality: str = "HIGH"
    asset_type: str
    expected_monitoring: bool = True


class AlertCanonical(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: str
    alert_id: str
    alert_timestamp: datetime
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    category: str  # RANSOMWARE, BRUTE_FORCE, DATA_EXFILTRATION, etc.
    source_system: Optional[str] = None
    asset_id: Optional[str] = None
    acknowledged_timestamp: Optional[datetime] = None
    investigation_started_timestamp: Optional[datetime] = None
    closed_timestamp: Optional[datetime] = None
    disposition: Optional[str] = None  # TRUE_POSITIVE, FALSE_POSITIVE, BENIGN, UNKNOWN
    escalated: Optional[bool] = None
    escalation_timestamp: Optional[datetime] = None
    investigator_id: Optional[str] = None
    root_cause_recorded: Optional[bool] = False
    remediation_recorded: Optional[bool] = False
    evidence_present: Optional[bool] = False
    status: Optional[str] = "CLOSED"  # OPEN, CLOSED, IN_PROGRESS, ESCALATED
    raw_data: Optional[Dict[str, Any]] = None


class CaseCanonical(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: str
    case_id: str
    alert_id: Optional[str] = None
    created_at: datetime
    assigned_at: Optional[datetime] = None
    investigation_started_at: Optional[datetime] = None
    escalation_status: Optional[str] = None
    escalation_timestamp: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    disposition: Optional[str] = None
    root_cause: Optional[str] = None
    remediation: Optional[str] = None
    evidence: Optional[str] = None
    investigator: Optional[str] = None
    closure_reason: Optional[str] = None
