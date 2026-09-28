from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.alert import Alert


def prioritize_alert_review_samples(
    db: Session,
    entity_id: Optional[str] = None,
    assessment_period_id: Optional[str] = "2026-Q2",
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Intelligently selects a high-yield, diverse sample of alerts for supervisory inspection.
    Balances severity, rapid closure anomalies, missing evidence, and unescalated critical threats.
    """
    q = db.query(Alert)
    if entity_id:
        q = q.filter(Alert.entity_id == entity_id)
    if assessment_period_id:
        q = q.filter(Alert.assessment_period_id == assessment_period_id)

    alerts = q.all()
    if not alerts and assessment_period_id:
        # Fallback to all periods if period filter empty
        alerts = db.query(Alert).all() if not entity_id else db.query(Alert).filter(Alert.entity_id == entity_id).all()

    if not alerts:
        return []

    scored_alerts = []
    seen_categories = set()

    for a in alerts:
        score = 0.0
        reasons = []

        # 1. Severity weight
        if a.severity == "CRITICAL":
            score += 35.0
            reasons.append("Critical severity operational threat")
        elif a.severity == "HIGH":
            score += 20.0
            reasons.append("High severity threat event")

        # 2. Closure speed anomaly
        if a.closed_timestamp and a.alert_timestamp:
            dur_m = (a.closed_timestamp - a.alert_timestamp).total_seconds() / 60.0
            if dur_m < 8.0 and a.severity in ["CRITICAL", "HIGH"]:
                score += 30.0
                reasons.append(f"Unusually rapid closure ({dur_m:.1f} mins) with minimal triage time")

        # 3. Critical alert without escalation
        if a.severity == "CRITICAL" and not a.escalated:
            score += 25.0
            reasons.append("Critical alert closed with no supervisory or Tier-2 escalation")

        # 4. Missing investigation evidence
        if a.evidence_present is False and a.severity in ["CRITICAL", "HIGH"]:
            score += 20.0
            reasons.append("Zero investigative artifacts, PCAP, or proof attached")

        # 5. Missing root cause & remediation
        if a.root_cause_recorded is False and a.remediation_recorded is False:
            score += 10.0
            reasons.append("No permanent remediation or root-cause recorded")

        # 6. Diversity bonus for unique categories
        if a.category not in seen_categories:
            score += 15.0
            seen_categories.add(a.category)

        if score > 0:
            closure_mins = None
            if a.closed_timestamp and a.alert_timestamp:
                closure_mins = round((a.closed_timestamp - a.alert_timestamp).total_seconds() / 60.0, 1)

            scored_alerts.append({
                "alert_id": a.alert_id,
                "entity_id": a.entity_id,
                "assessment_period_id": a.assessment_period_id,
                "alert_timestamp": a.alert_timestamp.isoformat() if a.alert_timestamp else None,
                "severity": a.severity,
                "category": a.category,
                "asset_id": a.asset_id,
                "disposition": a.disposition,
                "closure_minutes": closure_mins,
                "escalated": a.escalated,
                "evidence_present": a.evidence_present,
                "priority_score": round(score, 1),
                "review_rationale": " • ".join(reasons)
            })

    # Sort descending by priority score
    scored_alerts.sort(key=lambda x: x["priority_score"], reverse=True)

    # Pick diverse top samples
    diverse_sample: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = {}

    for item in scored_alerts:
        cat = item["category"]
        if category_counts.get(cat, 0) < 3:  # Max 3 per category for diversity
            diverse_sample.append(item)
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if len(diverse_sample) >= limit:
                break

    return diverse_sample
