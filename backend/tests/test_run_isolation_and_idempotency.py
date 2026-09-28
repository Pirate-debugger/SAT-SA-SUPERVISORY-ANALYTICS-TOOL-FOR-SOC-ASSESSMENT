import pytest
from app.analytics.engine import execute_supervisory_analysis_run
from app.models.analysis_run import AnalysisRun
from app.models.finding import Finding
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


def test_analysis_run_isolation_and_idempotency(db_session):
    """
    Section 4 Verification:
    Repeated execution of the same dataset, period, and ruleset must be idempotent
    and MUST NOT create duplicate active findings or inflate risk.
    """
    period = "2026-TEST-IDEMP"
    ent_id = "CSE-IDEMP-01"

    ent = Entity(
        entity_id=ent_id,
        name="Test Entity Idempotency",
        sector="DEFENSE",
        claimed_tier="TIER_1",
        monitored_asset_count=10
    )
    db_session.merge(ent)
    db_session.commit()

    # Execution 1
    run1 = execute_supervisory_analysis_run(
        db=db_session,
        entity_ids=[ent_id],
        assessment_period_id=period,
        dataset_version="v1.0-test",
        note="Initial Run",
        force_rerun=False
    )
    findings_count_1 = db_session.query(Finding).filter(Finding.run_id == run1.run_id).count()

    # Execution 2 with SAME inputs (without force_rerun) -> Must return the existing run!
    run2 = execute_supervisory_analysis_run(
        db=db_session,
        entity_ids=[ent_id],
        assessment_period_id=period,
        dataset_version="v1.0-test",
        note="Duplicate Execution Attempt",
        force_rerun=False
    )

    assert run1.run_id == run2.run_id
    assert run1.config_hash == run2.config_hash

    # Check total active findings for this run
    findings_count_2 = db_session.query(Finding).filter(Finding.run_id == run2.run_id).count()
    assert findings_count_1 == findings_count_2

    # Verify run isolation: only ONE run marked is_latest for this period
    latest_runs = db_session.query(AnalysisRun).filter(
        AnalysisRun.assessment_period_id == period,
        AnalysisRun.is_latest.is_(True)
    ).all()
    assert len(latest_runs) == 1
    assert latest_runs[0].run_id == run1.run_id
