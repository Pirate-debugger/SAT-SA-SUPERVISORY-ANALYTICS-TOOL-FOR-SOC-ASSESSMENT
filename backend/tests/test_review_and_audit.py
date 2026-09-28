import pytest
import json
from app.models.audit import AuditLog, ReviewItem
from app.models.finding import Finding
from app.api.reviews import update_review_item
from app.schemas.response import ReviewActionRequest
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


def test_review_workflow_and_no_auto_confirmation(db_session):
    """
    Section 19 Verification:
    - Supported statuses: OPEN, UNDER_REVIEW, CONFIRMED, REJECTED, DEFERRED, REQUEST_EVIDENCE.
    - REVIEWED must map to UNDER_REVIEW, NOT CONFIRMED (review is not confirmation!).
    """
    fnd = Finding(
        finding_id="FND-REV-01",
        run_id="RUN-REV-01",
        entity_id="CSE-REV-01",
        assessment_period_id="2026-Q2",
        finding_type="EXECUTION_GAP_RAPID_CLOSURE",
        category="EXECUTION_GAP",
        severity="HIGH",
        confidence=0.9,
        reason="Test Rapid Closure",
        evidence_summary="Test evidence",
        status="OPEN"
    )
    db_session.merge(fnd)

    rev = ReviewItem(
        review_id="REV-ITEM-01",
        finding_id="FND-REV-01",
        entity_id="CSE-REV-01",
        assessment_period_id="2026-Q2",
        run_id="RUN-REV-01",
        priority="HIGH",
        status="OPEN"
    )
    db_session.merge(rev)
    db_session.commit()

    # Action 1: Supervisor marks as REVIEWED -> must map to UNDER_REVIEW, NOT CONFIRMED
    action_req = ReviewActionRequest(
        status="REVIEWED",
        assigned_reviewer="Supervisor Sarah",
        notes="First pass inspection conducted.",
        action_name="SUPERVISOR_INSPECTION"
    )
    updated = update_review_item(review_id="REV-ITEM-01", action=action_req, db=db_session)
    assert updated.status == "UNDER_REVIEW"
    assert updated.status != "CONFIRMED"

    # Action 2: Explicit supervisor confirmation
    action_confirm = ReviewActionRequest(
        status="CONFIRMED",
        assigned_reviewer="Supervisor Sarah",
        notes="Operational execution gap confirmed with CSE.",
        action_name="FORMAL_CONFIRMATION"
    )
    confirmed = update_review_item(review_id="REV-ITEM-01", action=action_confirm, db=db_session)
    assert confirmed.status == "CONFIRMED"


def test_tamper_evident_audit_chain(db_session):
    """
    Section 20 Verification:
    Verifies that the audit trail uses a SHA-256 hash chain and catches tampering.
    """
    entry1 = AuditLog.create_entry(
        db=db_session,
        action="TEST_ACTION_1",
        actor="SUPERVISOR_1",
        entity_id="CSE-AUDIT-01",
        details={"event": "initial_assessment"}
    )
    entry2 = AuditLog.create_entry(
        db=db_session,
        action="TEST_ACTION_2",
        actor="SUPERVISOR_2",
        entity_id="CSE-AUDIT-01",
        details={"event": "review_completed"}
    )

    try:
        # Clean chain verification
        verify_result = AuditLog.verify_chain(db_session)
        assert verify_result["verified"] is True
        assert len(verify_result["tampered_events"]) == 0

        # Simulate malicious database tampering by altering details of entry1 directly
        entry1.details_json = json.dumps({"event": "maliciously_tampered_record"})
        db_session.commit()

        # Re-verify -> Must detect tamper!
        tamper_result = AuditLog.verify_chain(db_session)
        assert tamper_result["verified"] is False
        assert len(tamper_result["tampered_events"]) > 0
        assert entry1.id in tamper_result["tampered_events"]
    finally:
        db_session.delete(entry2)
        db_session.delete(entry1)
        db_session.commit()

