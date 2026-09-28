import pytest
from datetime import datetime, timezone, timedelta
from app.analytics.peer_benchmarking import evaluate_peer_benchmarking, compute_robust_baseline
from app.analytics.anomaly_engine import detect_operational_anomalies
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


def test_robust_statistical_primitives():
    """Verifies that median, MAD, and IQR computed by compute_robust_baseline are robust to outliers."""
    # Data with extreme outlier (1000)
    data = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 1000.0]
    base = compute_robust_baseline(data)

    assert base["median"] == 14.0
    assert base["mad"] < 5.0  # MAD is not inflated by 1000
    assert base["iqr"] <= 5.0  # IQR is not inflated by 1000
    assert base["status"] == "VALID_SAMPLE"



def test_anomaly_creates_first_class_finding(db_session):
    """Verifies that operational anomalies produce first-class findings (Section 12)."""
    period = "2026-TEST-ANOM"
    ent_id = "CSE-ANOM-01"

    ent = Entity(
        entity_id=ent_id,
        name="Test Entity Anomalies",
        sector="FINANCIAL",
        claimed_tier="TIER_1",
        monitored_asset_count=10
    )
    db_session.merge(ent)

    # Add 10 alerts with suspiciously rapid closure (10 seconds)
    now = datetime.now(timezone.utc)
    for i in range(10):
        db_session.add(Alert(
            alert_id=f"ALT-ANOM-{i}",
            entity_id=ent_id,
            assessment_period_id=period,
            alert_timestamp=now,
            closed_timestamp=now + timedelta(seconds=10),
            category="UNUSUAL_LOGIN",
            severity="CRITICAL",
            status="CLOSED",
            asset_id="AST-01"
        ))
    db_session.commit()

    summary, findings = detect_operational_anomalies(
        db_session,
        assessment_period_id=period,
        run_id="RUN-TEST-ANOM"
    )

    assert summary["anomalies_detected"] >= 1
    assert len(findings) >= 1
    for f, ev in findings:
        assert f.category == "ANOMALY"
        assert f.confidence > 0.0
        assert f.finding_id.startswith("FND-ANOM-")


