import pytest
from datetime import datetime, timezone
from app.analytics.capability_dimensions import (
    evaluate_8_capability_dimensions,
    DIMENSION_NAMES
)
from app.analytics.engine import calculate_supervisory_attention_indicator
from app.models.entity import Entity
from app.models.alert import Alert
from app.models.case import Case
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_eight_capability_dimensions_structure(db_session):
    """Verifies that all 8 dimensions are evaluated from evidence with status and observed metrics."""
    period = "2026-TEST-CAP"
    ent_id = "CSE-CAP-01"

    ent = Entity(
        entity_id=ent_id,
        name="Test Entity Capabilities",
        sector="ENERGY",
        claimed_tier="TIER_1",
        monitored_asset_count=20
    )
    db_session.merge(ent)

    # Add sample alerts and cases
    for i in range(5):
        db_session.add(Alert(
            alert_id=f"ALT-CAP-{i}",
            entity_id=ent_id,
            assessment_period_id=period,
            alert_timestamp=datetime.now(timezone.utc),
            category="MALWARE_DETECTION",
            severity="HIGH",
            status="CLOSED",
            asset_id=f"AST-{i}"
        ))
        db_session.add(Case(
            case_id=f"CS-CAP-{i}",
            entity_id=ent_id,
            assessment_period_id=period,
            created_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
            disposition="RESOLVED",
            investigator="analyst_1",
            closure_reason="Standard analysis conducted.",
            evidence='["log_1"]'
        ))
    db_session.commit()

    dim_scores = evaluate_8_capability_dimensions(
        db_session,
        run_id="RUN-TEST-CAP",
        entity_id=ent_id,
        assessment_period_id=period
    )

    assert len(dim_scores) == 8
    dim_names = [d.dimension for d in dim_scores]
    for exp in DIMENSION_NAMES:
        assert exp in dim_names

    # Check each score has valid status
    valid_statuses = {"STRONG EVIDENCE", "ATTENTION", "INSUFFICIENT EVIDENCE", "NOT ASSESSED"}
    for d in dim_scores:
        assert d.status in valid_statuses
        assert 0.0 <= d.score <= 100.0
        assert d.confidence > 0.0


def test_supervisory_attention_indicator_breakdown():
    """Verifies that the attention indicator is deterministic and provides category breakdown."""
    findings_summary = {
        "execution_gaps_count": 3,
        "negative_space_count": 2,
        "anomalies_count": 1,
        "critical_findings_count": 2,
        "high_findings_count": 2
    }
    cap_profile = {
        "INVESTIGATION": {"score": 45.0, "status": "ATTENTION"},
        "ESCALATION": {"score": 50.0, "status": "ATTENTION"},
        "OPERATIONAL_DISCIPLINE": {"score": 85.0, "status": "STRONG EVIDENCE"}
    }
    peer_deviations = [{"metric": "rapid_closure", "deviation": 3.2}]
    temporal_profile = {"coverage_trend": {"slope": -0.15, "persistence": 3}}

    level, indicator, breakdown = calculate_supervisory_attention_indicator(
        findings_summary,
        cap_profile,
        peer_deviations,
        temporal_profile
    )

    assert 0.0 <= indicator <= 100.0
    assert level in {"CRITICAL", "HIGH", "MODERATE", "LOW"}
    assert "Execution Gaps" in breakdown
    assert "Negative Space" in breakdown
    assert "Investigation" in breakdown
    assert "Temporal Persistence" in breakdown
    assert breakdown["Execution Gaps"] > 0

