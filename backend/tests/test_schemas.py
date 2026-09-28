from datetime import datetime
import pytest
from pydantic import ValidationError
from app.schemas.canonical import AlertCanonical, CaseCanonical, EntityBase, AssetBase


def test_alert_canonical_valid():
    alert = AlertCanonical(
        entity_id="CSE-POWER-01",
        alert_id="ALT-1001",
        alert_timestamp=datetime(2026, 1, 15, 10, 30, 0),
        severity="CRITICAL",
        category="RANSOMWARE",
        source_system="EDR-SENSOR",
        asset_id="AST-001",
        root_cause_recorded=True,
        remediation_recorded=False,
        evidence_present=True,
        status="CLOSED"
    )
    assert alert.entity_id == "CSE-POWER-01"
    assert alert.severity == "CRITICAL"
    assert alert.root_cause_recorded is True
    assert alert.remediation_recorded is False


def test_alert_canonical_missing_required():
    # Missing alert_timestamp
    with pytest.raises(ValidationError):
        AlertCanonical(
            entity_id="CSE-POWER-01",
            alert_id="ALT-1002",
            severity="HIGH",
            category="BRUTE_FORCE"
        )


def test_case_canonical_valid():
    case = CaseCanonical(
        entity_id="CSE-BANK-02",
        case_id="CAS-5001",
        alert_id="ALT-1001",
        created_at=datetime(2026, 1, 15, 11, 0, 0),
        disposition="TRUE_POSITIVE",
        closure_reason="Firewall rule applied"
    )
    assert case.case_id == "CAS-5001"
    assert case.disposition == "TRUE_POSITIVE"
    assert case.closed_at is None
