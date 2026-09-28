import pytest
from app.analytics.validation_harness import (
    run_synthetic_ground_truth_benchmark,
    evaluate_expert_review_mode
)
from app.models.audit import ExpertReviewLabel
from app.models.analysis_run import AnalysisRun
from app.time_utils import utc_now
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_mode_a_synthetic_ground_truth_benchmark(db_session):
    """
    Section 21A Verification:
    Synthetic Ground Truth benchmark must compute TP, FP, TN, FN, Precision, Recall, F1.
    FPR must only be calculated against explicit negative controls.
    """
    # Find or use the latest run
    latest = db_session.query(AnalysisRun).first()
    run_id = latest.run_id if latest else "RUN-BENCHMARK-TEST"

    benchmark = run_synthetic_ground_truth_benchmark(db_session, run_id=run_id)

    assert "confusion_matrix" in benchmark
    cm = benchmark["confusion_matrix"]
    assert "true_positives" in cm
    assert "false_positives" in cm
    assert "true_negatives" in cm
    assert "false_negatives" in cm
    assert "performance_metrics" in benchmark
    m = benchmark["performance_metrics"]
    assert 0.0 <= m["precision"] <= 1.0
    assert 0.0 <= m["recall"] <= 1.0
    assert 0.0 <= m["f1_score"] <= 1.0



def test_mode_b_expert_review_mode(db_session):
    """
    Section 21B Verification:
    Human expert review calibration evaluates human labels against system findings.
    Must not claim expert validated if insufficient expert labels exist.
    """
    # 1. When no expert labels exist
    db_session.query(ExpertReviewLabel).delete()
    db_session.commit()

    eval_empty = evaluate_expert_review_mode(db_session, run_id="RUN-EXP-01")
    assert eval_empty["sufficient_expert_data"] is False
    assert "AWAITING_EXPERT_LABELS" in eval_empty["status"]


    # 2. Add an expert label
    lbl = ExpertReviewLabel(
        target_type="FINDING",
        target_id="FND-EXP-01",
        entity_id="CSE-EXP-01",
        assessment_period_id="2026-Q2",
        expert_label="CONFIRMED_GAP",
        severity="HIGH",
        evidence_notes="Analyst agreed this was a severe execution gap.",
        reviewer_name="Dr. Senior Reviewer",
        created_at=utc_now()
    )
    db_session.add(lbl)
    db_session.commit()

    eval_with_label = evaluate_expert_review_mode(db_session, run_id="RUN-EXP-01")
    assert eval_with_label["total_expert_labels"] >= 1
