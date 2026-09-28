import pytest
from datetime import datetime, date, timezone
from app.models.entity import Entity, AssessmentPeriod
from app.models.alert import Alert
from app.models.finding import Finding
from app.analytics.temporal_drift import evaluate_temporal_drift
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_temporal_drift_multi_period_analysis(db_session):
    """
    Section 13 Verification:
    Tests period-over-period comparison, regression slope calculation,
    persistence, deterioration signals, and emerging/resolved weaknesses.
    """
    # 1. Setup multi-period assessment framework
    periods_data = [
        ("2025-Q3", "Q3 2025 Assessment", date(2025, 7, 1), date(2025, 9, 30)),
        ("2025-Q4", "Q4 2025 Assessment", date(2025, 10, 1), date(2025, 12, 31)),
        ("2026-Q1", "Q1 2026 Assessment", date(2026, 1, 1), date(2026, 3, 31)),
        ("2026-Q2", "Q2 2026 Assessment", date(2026, 4, 1), date(2026, 6, 30)),
    ]
    for pid, pname, s_date, e_date in periods_data:
        p = db_session.query(AssessmentPeriod).filter(AssessmentPeriod.period_id == pid).first()
        if not p:
            db_session.add(AssessmentPeriod(period_id=pid, name=pname, start_date=s_date, end_date=e_date, is_active=True))
    db_session.commit()

    # 2. Setup entity with progressive coverage deterioration (Section 13 example: 96% -> 94% -> 83% -> 66%)
    ent_id = "CSE-DRIFT-01"
    ent = db_session.query(Entity).filter(Entity.entity_id == ent_id).first()
    if not ent:
        ent = Entity(
            entity_id=ent_id,
            name="Deteriorating Power Grid Corp",
            sector="ENERGY",
            claimed_tier="TIER_1",
            monitored_asset_count=100
        )
        db_session.add(ent)
        db_session.commit()

    # Add active assets reflecting 96% -> 94% -> 83% -> 66% coverage (coverage gap: 4% -> 6% -> 17% -> 34%)
    active_asset_counts = {"2025-Q3": 96, "2025-Q4": 94, "2026-Q1": 83, "2026-Q2": 66}
    for pid, count in active_asset_counts.items():
        # Clear existing test alerts for entity in period
        db_session.query(Alert).filter(Alert.entity_id == ent_id, Alert.assessment_period_id == pid).delete()
        for i in range(count):
            db_session.add(Alert(
                alert_id=f"ALT-DRIFT-{pid}-{i}",
                entity_id=ent_id,
                assessment_period_id=pid,
                alert_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                category="SUSPICIOUS_AUTHENTICATION",
                severity="MEDIUM",
                status="CLOSED",
                asset_id=f"ASSET-DRIFT-{i}",
                evidence_present=True
            ))
    db_session.commit()

    # Add persistent finding in multiple periods and newly emerging finding in latest
    db_session.query(Finding).filter(Finding.entity_id == ent_id).delete()
    db_session.add(Finding(
        finding_id="FND-PERSIST-1",
        run_id="RUN-DRIFT-2025Q4",
        entity_id=ent_id,
        assessment_period_id="2025-Q4",
        finding_type="REPEAT_UNREMEDIATED_ALERT",
        category="EXECUTION_GAP",
        severity="HIGH",
        reason="Repeated un-remediated alerts detected across assets.",
        evidence_summary="Alert telemetry showed identical signature recurring."
    ))
    db_session.add(Finding(
        finding_id="FND-PERSIST-2",
        run_id="RUN-DRIFT-2026Q2",
        entity_id=ent_id,
        assessment_period_id="2026-Q2",
        finding_type="REPEAT_UNREMEDIATED_ALERT",
        category="EXECUTION_GAP",
        severity="HIGH",
        reason="Repeated un-remediated alerts detected across assets.",
        evidence_summary="Alert telemetry showed identical signature recurring."
    ))
    db_session.add(Finding(
        finding_id="FND-EMERGING-1",
        run_id="RUN-DRIFT-2026Q2",
        entity_id=ent_id,
        assessment_period_id="2026-Q2",
        finding_type="CRITICAL_CLOSURE_TOO_FAST",
        category="EXECUTION_GAP",
        severity="CRITICAL",
        reason="Critical alerts closed in under 3 minutes without triage.",
        evidence_summary="Median closure time was 110s."
    ))
    db_session.commit()

    # 3. Evaluate temporal drift
    drift_result = evaluate_temporal_drift(db_session, entity_id=ent_id)
    assert ent_id in drift_result["entity_trends"]

    trend = drift_result["entity_trends"][ent_id]
    assert len(trend["period_metrics"]) >= 4

    # Verify slope is positive (coverage gap widening steadily)
    assert trend["coverage_slope"] > 0
    assert len(trend["step_changes"]) >= 3

    # Verify persistence tracking
    assert "REPEAT_UNREMEDIATED_ALERT" in trend["persistent_weaknesses"]
    assert "CRITICAL_CLOSURE_TOO_FAST" in trend["newly_emerging_weaknesses"]

    # Verify deterioration signals include coverage deterioration
    drift_types = [s["drift_type"] for s in trend["deterioration_signals"]]
    assert "SUSTAINED_MONITORING_COVERAGE_DETERIORATION" in drift_types
    assert trend["overall_trajectory"] == "DETERIORATING"
