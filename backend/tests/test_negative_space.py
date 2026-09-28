import pytest
from datetime import datetime, timezone
from app.analytics.negative_space import evaluate_negative_space_for_entity
from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_negative_space_silent_assets(db_session):
    """Verifies that the Expectation Engine flags critical assets producing zero telemetry."""
    period = "2026-TEST-NEG"
    ent_id = "CSE-NEG-01"

    ent = Entity(
        entity_id=ent_id,
        name="Test Entity Negative Space",
        sector="FINANCIAL",
        claimed_tier="TIER_1",
        monitored_asset_count=5
    )
    db_session.merge(ent)

    # Add 2 assets: 1 silent critical asset, 1 active asset
    db_session.merge(Asset(
        asset_id="CORE-SWIFT-01",
        entity_id=ent_id,
        hostname="swift-prod-01",
        ip_address="10.10.10.1",
        criticality="CRITICAL",
        asset_type="CORE_SERVER",
        expected_monitoring=True
    ))
    db_session.merge(Asset(
        asset_id="WEB-PORTAL-01",
        entity_id=ent_id,
        hostname="web-prod-01",
        ip_address="10.10.10.2",
        criticality="LOW",
        asset_type="WEB_SERVER",
        expected_monitoring=True
    ))

    # Add an alert only for WEB-PORTAL-01 (CORE-SWIFT-01 remains completely silent)
    db_session.add(Alert(
        alert_id="ALT-NEG-01",
        entity_id=ent_id,
        assessment_period_id=period,
        alert_timestamp=datetime.now(timezone.utc),
        category="WEB_ATTACK",
        severity="LOW",
        status="CLOSED",
        asset_id="WEB-PORTAL-01"
    ))
    db_session.commit()

    findings = evaluate_negative_space_for_entity(
        db_session,
        run_id="RUN-TEST-NEG",
        entity_id=ent_id,
        assessment_period_id=period
    )

    finding_types = [f.finding_type for f, _ in findings]
    assert "CRITICAL_ASSET_TELEMETRY_SILENCE" in finding_types

    # Find the critical asset silence finding
    target_f = next(f for f, _ in findings if f.finding_type == "CRITICAL_ASSET_TELEMETRY_SILENCE")
    assert target_f.category == "NEGATIVE_SPACE"
    assert "silent assets" in target_f.evidence_summary.lower()
    assert "POTENTIAL NEGATIVE SPACE" in target_f.reason or "COVERAGE GAP" in target_f.reason
