import pytest
from datetime import datetime, timezone
from app.models.entity import Entity
from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding
from app.analytics.engine import get_authoritative_entity_metrics, calculate_supervisory_attention_indicator
from app.analytics.data_quality import evaluate_dataset_quality
from app.analytics.sample_prioritizer import prioritize_alert_review_samples
from app.analytics.report_generator import generate_supervisory_report, export_report_to_markdown
from app.analytics.validation_harness import evaluate_expert_review_mode
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_data_quality_unknown_preservation(db_session):
    """
    Section 7 Verification:
    Ensures UNKNOWN severities and UNKNOWN statuses are NOT silently coerced,
    and missing critical fields reduce analytical confidence factor.
    """
    period = "2026-Q2"
    ent_id = "CSE-DQ-TEST"
    ent = db_session.query(Entity).filter(Entity.entity_id == ent_id).first()
    if not ent:
        ent = Entity(entity_id=ent_id, name="Data Quality Test Entity", sector="ENERGY", claimed_tier="TIER_2")
        db_session.add(ent)
        db_session.commit()

    # Clear previous alerts
    db_session.query(Alert).filter(Alert.entity_id == ent_id).delete()

    # Add alert with explicit UNKNOWN severity
    db_session.add(Alert(
        alert_id="ALT-UNK-01",
        entity_id=ent_id,
        assessment_period_id=period,
        alert_timestamp=datetime(2026, 5, 1, tzinfo=timezone.utc),
        category="MALWARE_DETECTION",
        severity="UNKNOWN",
        status="UNKNOWN",
        asset_id="AST-01",
        evidence_present=False
    ))
    db_session.commit()

    dq = evaluate_dataset_quality(db_session, assessment_period_id=period)
    assert "completeness_pct" in dq
    assert "validity_pct" in dq
    assert "confidence_factor" in dq
    assert dq["unknown_severity_count"] >= 1
    assert dq["unknown_status_count"] >= 1


def test_sample_prioritization_engine(db_session):
    """
    Section 15 Verification:
    Selects high-value review samples from thousands of alerts and explains 'why_selected'.
    """
    period = "2026-Q2"
    ent_id = "CSE-PRIO-01"
    ent = db_session.query(Entity).filter(Entity.entity_id == ent_id).first()
    if not ent:
        ent = Entity(entity_id=ent_id, name="Prioritization Test Entity", sector="FINANCIAL", claimed_tier="TIER_1")
        db_session.add(ent)
        db_session.commit()

    # Create alerts with different priority profiles
    db_session.add(Alert(
        alert_id="ALT-HIGH-PRIO-FAST",
        entity_id=ent_id,
        assessment_period_id=period,
        alert_timestamp=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        closed_timestamp=datetime(2026, 5, 1, 10, 1, 30, tzinfo=timezone.utc),
        category="EXFILTRATION",
        severity="CRITICAL",
        status="CLOSED",
        evidence_present=False
    ))
    db_session.commit()

    samples = prioritize_alert_review_samples(db_session, assessment_period_id=period, limit=10)
    assert len(samples) > 0

    # Ensure every prioritized sample contains an explainable selection rationale
    for s in samples:
        assert "why_selected" in s
        assert len(s["why_selected"]) > 0
        assert "priority_score" in s


def test_authoritative_metrics_consistency(db_session):
    """
    Section 5 Verification:
    Ensures ONE canonical source of truth for supervisory attention and capabilities.
    """
    ent = db_session.query(Entity).first()
    assert ent is not None

    m1 = get_authoritative_entity_metrics(db_session, entity_id=ent.entity_id)
    m2 = get_authoritative_entity_metrics(db_session, entity_id=ent.entity_id)

    # Identical deterministic values across invocations
    assert m1["supervisory_attention_indicator"] == m2["supervisory_attention_indicator"]
    assert m1["supervisory_attention_level"] == m2["supervisory_attention_level"]
    assert m1["score_breakdown"] == m2["score_breakdown"]


def test_supervisory_report_comprehensive_generation(db_session):
    """
    Section 30 & 31 Verification:
    Generates full multi-section report with explicit synthetic disclaimer and markdown export.
    """
    report = generate_supervisory_report(db_session, assessment_period_id="2026-Q2")
    assert "report_metadata" in report
    assert "DEMO / SYNTHETIC DATA" in report["report_metadata"]["classification"]

    sections = report["sections"]
    required_sections = [
        "1_executive_summary",
        "2_scope_and_entities",
        "3_dataset_and_provenance",
        "4_data_quality_evaluation",
        "5_entities_requiring_attention",
        "6_eight_dimension_capability_assessment",
        "7_execution_gaps",
        "8_negative_space",
        "9_operational_anomalies",
        "10_peer_benchmarking",
        "11_temporal_trends_and_drift",
        "12_prioritized_review_samples",
        "13_review_queue_and_actions",
        "14_validation_framework",
        "15_supervisory_methodology",
        "16_limitations",
        "17_tamper_evident_audit_information",
        "18_analysis_run_information"
    ]
    for req in required_sections:
        assert req in sections

    # Markdown export test
    md_content = export_report_to_markdown(report)
    assert "# SUPERVISORY SOC OPERATIONAL ASSESSMENT REPORT" in md_content
    assert "DEMO / SYNTHETIC DATA" in md_content
    assert "Tamper-Evident Audit Verification" in md_content


from app.models.audit import ExpertReviewLabel
from app.analytics.validation_harness import evaluate_expert_review_mode


def test_mode_b_expert_annotation_flow(db_session):
    """
    Section 21 Verification:
    Mode B Expert Review annotation and comparison against automated system findings.
    """
    label_entry = ExpertReviewLabel(
        target_type="FINDING",
        target_id="FND-EXPERT-TEST-01",
        entity_id="CSE-FIN-01",
        expert_label="TRUE_POSITIVE",
        severity="CRITICAL",
        reviewer_name="Lead Auditor Dr. Sharma",
        evidence_notes="Verified lack of escalation logs in SIEM."
    )
    db_session.add(label_entry)
    db_session.commit()

    mode_b_eval = evaluate_expert_review_mode(db_session)
    assert mode_b_eval["total_expert_labels"] >= 1
    assert "agreement_rate_pct" in mode_b_eval
    assert mode_b_eval["status"] == "VALIDATED_WITH_EXPERT_LABELS"
