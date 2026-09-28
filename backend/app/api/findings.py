import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finding import Finding, FindingEvidenceLink
from app.models.alert import Alert
from app.models.case import Case
from app.models.entity import Asset
from app.schemas.analysis import FindingBase, FindingDetailOut, FindingEvidenceLinkOut

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("", response_model=List[FindingBase])
def list_findings(
    entity_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Finding)
    if entity_id:
        q = q.filter(Finding.entity_id == entity_id)
    if category:
        q = q.filter(Finding.category == category)
    if severity:
        q = q.filter(Finding.severity == severity)
    if status:
        q = q.filter(Finding.status == status)
    if run_id:
        q = q.filter(Finding.run_id == run_id)

    findings = q.order_by(Finding.created_at.desc()).all()
    results = []
    for f in findings:
        results.append(FindingBase(
            finding_id=f.finding_id,
            run_id=f.run_id,
            entity_id=f.entity_id,
            finding_type=f.finding_type,
            category=f.category,
            severity=f.severity,
            confidence=f.confidence,
            reason=f.reason,
            evidence_summary=f.evidence_summary,
            metric_values=json.loads(f.metric_values_json) if f.metric_values_json else None,
            baseline=json.loads(f.baseline_json) if f.baseline_json else None,
            sample_size=f.sample_size,
            status=f.status,
            created_at=f.created_at
        ))
    return results


@router.get("/{finding_id}", response_model=FindingDetailOut)
def get_finding_detail(finding_id: str, db: Session = Depends(get_db)):
    f = db.query(Finding).filter(Finding.finding_id == finding_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")

    links = db.query(FindingEvidenceLink).filter(FindingEvidenceLink.finding_id == finding_id).all()
    evidence_records: List[FindingEvidenceLinkOut] = []

    for l in links:
        details = {}
        if l.record_type == "ALERT":
            alt = db.query(Alert).filter(Alert.alert_id == l.record_id).first()
            if alt:
                details = {
                    "alert_id": alt.alert_id,
                    "timestamp": alt.alert_timestamp.isoformat() if alt.alert_timestamp else None,
                    "severity": alt.severity,
                    "category": alt.category,
                    "asset_id": alt.asset_id,
                    "closed_timestamp": alt.closed_timestamp.isoformat() if alt.closed_timestamp else None,
                    "disposition": alt.disposition,
                    "escalated": alt.escalated,
                    "investigator_id": alt.investigator_id,
                    "evidence_present": alt.evidence_present,
                    "remediation_recorded": alt.remediation_recorded
                }
        elif l.record_type == "CASE":
            cas = db.query(Case).filter(Case.case_id == l.record_id).first()
            if cas:
                details = {
                    "case_id": cas.case_id,
                    "created_at": cas.created_at.isoformat() if cas.created_at else None,
                    "escalation_status": cas.escalation_status,
                    "disposition": cas.disposition,
                    "root_cause": cas.root_cause,
                    "remediation": cas.remediation,
                    "closure_reason": cas.closure_reason
                }
        elif l.record_type == "ASSET":
            ast = db.query(Asset).filter(Asset.asset_id == l.record_id).first()
            if ast:
                details = {
                    "asset_id": ast.asset_id,
                    "hostname": ast.hostname,
                    "ip_address": ast.ip_address,
                    "criticality": ast.criticality,
                    "asset_type": ast.asset_type
                }

        evidence_records.append(FindingEvidenceLinkOut(
            record_type=l.record_type,
            record_id=l.record_id,
            relevance_note=l.relevance_note,
            details=details
        ))

    return FindingDetailOut(
        finding_id=f.finding_id,
        run_id=f.run_id,
        entity_id=f.entity_id,
        finding_type=f.finding_type,
        category=f.category,
        severity=f.severity,
        confidence=f.confidence,
        reason=f.reason,
        evidence_summary=f.evidence_summary,
        metric_values=json.loads(f.metric_values_json) if f.metric_values_json else None,
        baseline=json.loads(f.baseline_json) if f.baseline_json else None,
        sample_size=f.sample_size,
        status=f.status,
        created_at=f.created_at,
        evidence_records=evidence_records
    )
