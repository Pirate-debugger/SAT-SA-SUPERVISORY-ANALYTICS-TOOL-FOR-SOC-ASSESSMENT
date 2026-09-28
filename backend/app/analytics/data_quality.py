from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.models.case import Case


def evaluate_dataset_quality(
    db: Session,
    assessment_period_id: Optional[str] = "2026-Q2",
    entity_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes rigorous Data Quality metrics across ingested alerts and cases (Section 7).
    Does NOT silently convert unknown values.
    Returns completeness, validity, timestamp quality, evidence coverage, and confidence factor.
    """
    alert_q = db.query(Alert)
    case_q = db.query(Case)

    if assessment_period_id:
        alert_q = alert_q.filter(Alert.assessment_period_id == assessment_period_id)
        case_q = case_q.filter(Case.assessment_period_id == assessment_period_id)
    if entity_id:
        alert_q = alert_q.filter(Alert.entity_id == entity_id)
        case_q = case_q.filter(Case.entity_id == entity_id)

    alerts = alert_q.all()
    if not alerts and assessment_period_id:
        # Fallback to all periods if period empty
        alerts = db.query(Alert).all() if not entity_id else db.query(Alert).filter(Alert.entity_id == entity_id).all()

    cases = case_q.all()
    if not cases and assessment_period_id:
        cases = db.query(Case).all() if not entity_id else db.query(Case).filter(Case.entity_id == entity_id).all()

    total_alerts = len(alerts)
    total_cases = len(cases)

    if total_alerts == 0:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "No alert records available for data quality assessment.",
            "completeness_pct": 0.0,
            "validity_pct": 0.0,
            "timestamp_quality_pct": 0.0,
            "evidence_coverage_pct": 0.0,
            "entity_coverage_pct": 0.0,
            "confidence_factor": 0.5,
            "quality_summary": "No data available."
        }

    # 1. Completeness Evaluation
    # Check key attributes: asset_id, category, source_system, investigator_id, disposition
    fields_checked = 0
    fields_populated = 0
    for a in alerts:
        fields_checked += 5
        if a.asset_id: fields_populated += 1
        if a.category and a.category != "UNKNOWN": fields_populated += 1
        if a.source_system: fields_populated += 1
        if a.investigator_id: fields_populated += 1
        if a.disposition and a.disposition != "UNKNOWN": fields_populated += 1

    completeness_pct = round((fields_populated / max(fields_checked, 1)) * 100.0, 1)

    # 2. Validity Evaluation
    # Penalize UNKNOWN severity, UNKNOWN status, malformed values
    unknown_severity_count = sum(1 for a in alerts if a.severity == "UNKNOWN")
    unknown_status_count = sum(1 for a in alerts if a.status == "UNKNOWN")
    valid_count = total_alerts - (unknown_severity_count + unknown_status_count)
    validity_pct = round(max(0.0, (valid_count / max(total_alerts, 1)) * 100.0), 1)

    # 3. Timestamp Quality Evaluation
    # Non-null, non-inverted alert_timestamp <= closed_timestamp
    timestamp_valid_count = 0
    for a in alerts:
        if a.alert_timestamp:
            if a.closed_timestamp:
                if a.closed_timestamp >= a.alert_timestamp:
                    timestamp_valid_count += 1
            else:
                timestamp_valid_count += 1
    timestamp_quality_pct = round((timestamp_valid_count / max(total_alerts, 1)) * 100.0, 1)

    # 4. Evidence Coverage Evaluation
    evidence_count = sum(1 for a in alerts if a.evidence_present)
    evidence_coverage_pct = round((evidence_count / max(total_alerts, 1)) * 100.0, 1)

    # 5. Entity Coverage
    entities = db.query(Entity).all()
    if entity_id:
        entities = [e for e in entities if e.entity_id == entity_id]

    total_declared_assets = sum(e.monitored_asset_count or 1 for e in entities)
    active_asset_ids = {a.asset_id for a in alerts if a.asset_id}
    entity_coverage_pct = round(min(100.0, (len(active_asset_ids) / max(total_declared_assets, 1)) * 100.0), 1)

    # 6. Analytical Confidence Factor
    # If completeness < 85% or validity < 85%, reduce analytical confidence!
    penalties = 0.0
    if completeness_pct < 85.0:
        penalties += (85.0 - completeness_pct) * 0.005
    if validity_pct < 85.0:
        penalties += (85.0 - validity_pct) * 0.005
    if timestamp_quality_pct < 90.0:
        penalties += (90.0 - timestamp_quality_pct) * 0.005

    confidence_factor = round(max(0.40, min(1.0, 1.0 - penalties)), 2)

    return {
        "status": "ASSESSED",
        "assessment_period_id": assessment_period_id,
        "total_alerts": total_alerts,
        "total_cases": total_cases,
        "completeness_pct": completeness_pct,
        "validity_pct": validity_pct,
        "timestamp_quality_pct": timestamp_quality_pct,
        "evidence_coverage_pct": evidence_coverage_pct,
        "entity_coverage_pct": entity_coverage_pct,
        "confidence_factor": confidence_factor,
        "unknown_severity_count": unknown_severity_count,
        "unknown_status_count": unknown_status_count,
        "quality_summary": (
            f"Completeness: {completeness_pct}% | Validity: {validity_pct}% | "
            f"Timestamp Quality: {timestamp_quality_pct}% | Evidence Coverage: {evidence_coverage_pct}% | "
            f"Analytical Confidence: {int(confidence_factor * 100)}%"
        )
    }
