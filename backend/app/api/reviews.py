import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import ReviewItem, AuditLog
from app.models.finding import Finding
from app.schemas.response import ReviewItemOut, ReviewActionRequest, AuditLogOut, AuditVerificationResult
from app.time_utils import utc_now

router = APIRouter(tags=["Review & Audit"])


@router.get("/review-queue", response_model=List[ReviewItemOut])
def get_review_queue(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    assessment_period_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(ReviewItem)
    if status:
        q = q.filter(ReviewItem.status == status)
    if priority:
        q = q.filter(ReviewItem.priority == priority)
    if entity_id:
        q = q.filter(ReviewItem.entity_id == entity_id)
    if assessment_period_id:
        q = q.filter(ReviewItem.assessment_period_id == assessment_period_id)

    items = q.order_by(ReviewItem.updated_at.desc()).all()
    results = []
    for item in items:
        f = db.query(Finding).filter(Finding.finding_id == item.finding_id).first()
        results.append(ReviewItemOut(
            review_id=item.review_id,
            finding_id=item.finding_id,
            entity_id=item.entity_id,
            assessment_period_id=item.assessment_period_id or (f.assessment_period_id if f else "2026-Q2"),
            run_id=item.run_id or (f.run_id if f else None),
            priority=item.priority,
            status=item.status,
            assigned_reviewer=item.assigned_reviewer,
            notes=item.notes,
            finding_reason=f.reason if f else None,
            finding_category=f.category if f else None,
            finding_severity=f.severity if f else None,
            capability_dimension=f.capability_dimension if f else None,
            recommended_review_area=f.recommended_review_area if f else None,
            updated_at=item.updated_at
        ))
    return results


@router.patch("/review-queue/{review_id}", response_model=ReviewItemOut)
def update_review_item(
    review_id: str,
    action: ReviewActionRequest,
    db: Session = Depends(get_db)
):
    item = db.query(ReviewItem).filter(ReviewItem.review_id == review_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    old_status = item.status
    
    # Section 19: Strict review workflow
    # Valid statuses: OPEN, UNDER_REVIEW, CONFIRMED, REJECTED, DEFERRED, REQUEST_EVIDENCE
    # Do NOT automatically map REVIEWED -> CONFIRMED (Review is NOT confirmation!)
    status_mapping = {
        "REVIEWED": "UNDER_REVIEW",
        "IN_REVIEW": "UNDER_REVIEW",
        "VERIFIED": "CONFIRMED",
        "DISMISSED": "REJECTED",
        "ESCALATED": "REQUEST_EVIDENCE",
        "HOLD": "DEFERRED",
        "DEFER": "DEFERRED",
    }
    raw_status = action.status.upper()
    normalized_status = status_mapping.get(raw_status, raw_status)
    valid_statuses = {"OPEN", "UNDER_REVIEW", "CONFIRMED", "REJECTED", "DEFERRED", "REQUEST_EVIDENCE"}
    if normalized_status not in valid_statuses:
        normalized_status = "UNDER_REVIEW"

    item.status = normalized_status
    now = utc_now()
    item.updated_at = now

    if action.assigned_reviewer:
        item.assigned_reviewer = action.assigned_reviewer
    if action.notes:
        existing_notes = item.notes or ""
        item.notes = f"{existing_notes}\n[{now.strftime('%Y-%m-%d %H:%M UTC')}] {action.notes}".strip()

    # Record past action in history
    history = json.loads(item.actions_history_json) if item.actions_history_json else []
    history.append({
        "timestamp": now.isoformat(),
        "action": action.action_name,
        "old_status": old_status,
        "new_status": normalized_status,
        "assigned_to": item.assigned_reviewer,
        "notes": action.notes
    })
    item.actions_history_json = json.dumps(history)

    # Sync finding status with explicit supervisor action
    f = db.query(Finding).filter(Finding.finding_id == item.finding_id).first()
    if f:
        f.status = normalized_status

    # Cryptographic Audit Log creation
    AuditLog.create_entry(
        db=db,
        action="SUPERVISORY_REVIEW_ACTION",
        actor="SUPERVISOR",
        entity_id=item.entity_id,
        details={
            "review_id": review_id,
            "finding_id": item.finding_id,
            "action": action.action_name,
            "old_status": old_status,
            "new_status": normalized_status,
            "reviewer": item.assigned_reviewer,
            "note_appended": bool(action.notes)
        }
    )
    db.commit()
    db.refresh(item)

    return ReviewItemOut(
        review_id=item.review_id,
        finding_id=item.finding_id,
        entity_id=item.entity_id,
        assessment_period_id=item.assessment_period_id or (f.assessment_period_id if f else "2026-Q2"),
        run_id=item.run_id or (f.run_id if f else None),
        priority=item.priority,
        status=item.status,
        assigned_reviewer=item.assigned_reviewer,
        notes=item.notes,
        finding_reason=f.reason if f else None,
        finding_category=f.category if f else None,
        finding_severity=f.severity if f else None,
        capability_dimension=f.capability_dimension if f else None,
        recommended_review_area=f.recommended_review_area if f else None,
        updated_at=item.updated_at
    )


@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return [
        AuditLogOut(
            id=log.id,
            timestamp=log.timestamp,
            action=log.action,
            entity_id=log.entity_id,
            actor=log.actor,
            details=json.loads(log.details_json) if log.details_json else None,
            previous_event_hash=log.previous_event_hash,
            event_hash=log.event_hash
        ) for log in logs
    ]


@router.get("/audit/verify", response_model=AuditVerificationResult)
def verify_audit_integrity(db: Session = Depends(get_db)):
    """Verifies cryptographic hash chain integrity of the supervisory audit trail."""
    result = AuditLog.verify_chain(db)
    return AuditVerificationResult(
        verified=result["verified"],
        total_events=result["total_events"],
        tampered_events=result["tampered_events"],
        root_hash=result["root_hash"],
        latest_hash=result["latest_hash"],
        status=result["status"],
        verification_timestamp=utc_now()
    )
