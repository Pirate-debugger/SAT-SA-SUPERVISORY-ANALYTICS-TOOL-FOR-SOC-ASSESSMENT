import pytest
from datetime import datetime, timezone, timedelta
from app.analytics.data_quality import evaluate_dataset_quality
from app.models.alert import Alert
from app.models.case import Case
from app.models.entity import Entity
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_data_quality_evaluation_basic(db_session):
    """Verifies that data quality engine calculates completeness, validity, and evidence coverage."""
    period = "2026-TEST-DQ"
    db_session.query(Alert).filter(Alert.assessment_period_id == period).delete()
    db_session.query(Case).filter(Case.assessment_period_id == period).delete()
    db_session.commit()

    # Create dummy entity
    ent = Entity(
        entity_id="CSE-DQ-01",
        name="Test Entity DQ",
        sector="FINANCIAL",
        claimed_tier="TIER_1",
        monitored_asset_count=10
    )
    db_session.merge(ent)

    # Insert an alert with UNKNOWN severity (must be preserved, not coerced to MEDIUM)
    al = Alert(
        alert_id="ALT-DQ-01",
        entity_id="CSE-DQ-01",
        assessment_period_id=period,
        alert_timestamp=datetime.now(timezone.utc),
        category="BRUTE_FORCE",
        severity="UNKNOWN",
        status="OPEN",
        asset_id="SRV-01",
        source_system="SIEM_SPLUNK",
        investigator_id="INV-01",
        disposition="TRUE_POSITIVE"
    )
    db_session.add(al)

    # Insert a case with evidence
    cs = Case(
        case_id="CS-DQ-01",
        entity_id="CSE-DQ-01",
        assessment_period_id=period,
        alert_id="ALT-DQ-01",
        created_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc) + timedelta(hours=2),
        investigator="analyst_test",
        evidence='["evidence_log_1", "evidence_pcap_1"]',
        closure_reason="Investigated thoroughly with logs and memory dumps."
    )
    db_session.add(cs)
    db_session.commit()

    dq_result = evaluate_dataset_quality(db_session, assessment_period_id=period, entity_id="CSE-DQ-01")

    assert dq_result["total_alerts"] >= 1
    assert dq_result["total_cases"] >= 1
    assert dq_result["unknown_severity_count"] >= 1
    assert dq_result["completeness_pct"] > 80.0
    # Section 7: UNKNOWN severity correctly reduces analytical confidence factor
    assert dq_result["confidence_factor"] <= 0.70


