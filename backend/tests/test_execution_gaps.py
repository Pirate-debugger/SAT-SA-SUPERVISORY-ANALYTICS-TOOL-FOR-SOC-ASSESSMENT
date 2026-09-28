import pytest
from datetime import datetime, timezone, timedelta
from app.analytics.execution_gaps import evaluate_execution_gaps_for_entity
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


def test_execution_gap_detection_and_traceability(db_session):
    """Verifies that execution gaps A-H are evaluated with explicit rule IDs and evidence links."""
    period = "2026-TEST-GAPS"
    ent_id = "CSE-GAP-01"

    ent = Entity(
        entity_id=ent_id,
        name="Test Entity Gaps",
        sector="TELECOM",
        claimed_tier="TIER_1",
        monitored_asset_count=15
    )
    db_session.merge(ent)

    # 1. Plant rapid closures (GAP-A): CRITICAL alerts closed in under 120 seconds
    now = datetime.now(timezone.utc)
    for i in range(4):
        db_session.add(Alert(
            alert_id=f"ALT-RAPID-{i}",
            entity_id=ent_id,
            assessment_period_id=period,
            alert_timestamp=now,
            closed_timestamp=now + timedelta(seconds=45),
            category="RANSOMWARE_BEHAVIOR",
            severity="CRITICAL",
            status="CLOSED",
            asset_id="CORE-TEL-01"
        ))

    # 2. Plant unescalated critical cases (GAP-C)
    for i in range(3):
        db_session.add(Case(
            case_id=f"CS-UNESC-{i}",
            entity_id=ent_id,
            assessment_period_id=period,
            alert_id=f"ALT-RAPID-{i}",
            created_at=now,
            closed_at=now + timedelta(hours=1),
            escalation_status="NOT_ESCALATED",
            evidence="[]",
            closure_reason="Closed without escalation"
        ))

    db_session.commit()

    findings = evaluate_execution_gaps_for_entity(
        db_session,
        run_id="RUN-TEST-GAPS",
        entity_id=ent_id,
        assessment_period_id=period
    )

    assert len(findings) >= 2
    rule_ids = [f.rule_id for f, _ in findings]
    assert any("GAP-A" in r for r in rule_ids)  # Rapid critical closure
    assert any("GAP-C" in r for r in rule_ids)  # Unescalated critical

    for f, ev_links in findings:
        assert f.category == "EXECUTION_GAP"
        assert f.entity_id == ent_id
        assert f.confidence > 0.0
        assert f.recommended_review_area is not None
        assert len(ev_links) > 0  # Evidence chain must connect to source records
