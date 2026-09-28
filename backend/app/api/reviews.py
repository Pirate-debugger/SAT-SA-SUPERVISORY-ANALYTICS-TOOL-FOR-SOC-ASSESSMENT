import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import ReviewItem, AuditLog
from app.models.finding import Finding
from app.schemas.response import ReviewItemOut, ReviewActionRequest, AuditLogOut

router = APIRouter(tags=["Review & Audit"])


@router.get("/review-queue", response_model=List[ReviewItemOut])
def get_review_queue(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(ReviewItem)
    if status:
        q = q.filter(ReviewItem.status == status)
    if priority:
        q = q.filter(ReviewItem.priority == priority)
    if entity_id:
        q = q.filter(ReviewItem.entity_id == entity_id)

    items = q.order_by(ReviewItem.updated_at.desc()).all()
    results = []
    for item in items:
        f = db.query(Finding).filter(Finding.finding_id == item.finding_id).first()
        results.append(ReviewItemOut(
            review_id=item.review_id,
            finding_id=item.finding_id,
            entity_id=item.entity_id,
            priority=item.priority,
            status=item.status,
            assigned_reviewer=item.assigned_reviewer,
            notes=item.notes,
            finding_reason=f.reason if f else None,
            finding_category=f.category if f else None,
            finding_severity=f.severity if f else None,
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
    item.status = action.status
    if action.assigned_reviewer:
        item.assigned_reviewer = action.assigned_reviewer
    if action.notes:
        existing_notes = item.notes or ""
        item.notes = f"{existing_notes}\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {action.notes}".strip()

    # Record past action
    history = json.loads(item.actions_history_json) if item.actions_history_json else []
    history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "action": action.action_name,
        "old_status": old_status,
        "new_status": action.status,
        "assigned_to": item.assigned_reviewer
    })
    item.actions_history_json = json.dumps(history)

    # Also update finding status if verified or dismissed
    f = db.query(Finding).filter(Finding.finding_id == item.finding_id).first()
    if f:
        if action.status in ["REVIEWED", "VERIFIED"]:
            f.status = "VERIFIED"
        elif action.status == "DISMISSED":
            f.status = "DISMISSED"

    # Add audit entry
    audit = AuditLog(
        action="SUPERVISORY_REVIEW_ACTION",
        entity_id=item.entity_id,
        actor="SUPERVISOR",
        details_json=json.dumps({
            "review_id": review_id,
            "finding_id": item.finding_id,
            "action": action.action_name,
            "new_status": action.status
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(item)

    return ReviewItemOut(
        review_id=item.review_id,
        finding_id=item.finding_id,
        entity_id=item.entity_id,
        priority=item.priority,
        status=item.status,
        assigned_reviewer=item.assigned_reviewer,
        notes=item.notes,
        finding_reason=f.reason if f else None,
        finding_category=f.category if f else None,
        finding_severity=f.severity if f else None,
        updated_at=item.updated_at
    )


@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        AuditLogOut(
            id=log.id,
            timestamp=log.timestamp,
            action=log.action,
            entity_id=log.entity_id,
            actor=log.actor,
            details=json.loads(log.details_json) if log.details_json else None
        ) for log in logs
    ]
