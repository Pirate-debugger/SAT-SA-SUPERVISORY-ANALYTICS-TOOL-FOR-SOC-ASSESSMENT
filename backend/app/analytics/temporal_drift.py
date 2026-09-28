from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.entity import Entity, AssessmentPeriod
from app.models.alert import Alert
from app.models.finding import Finding


def evaluate_temporal_drift(db: Session, entity_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes period-over-period capability drift and flags deterioration patterns.
    """
    periods = db.query(AssessmentPeriod).order_by(AssessmentPeriod.start_date.asc()).all()
    if len(periods) < 2:
        return {
            "status": "INSUFFICIENT_PERIODS",
            "message": "At least 2 assessment periods are required for temporal drift analysis.",
            "entity_trends": {}
        }

    period_ids = [p.period_id for p in periods]
    entities_query = db.query(Entity)
    if entity_id:
        entities_query = entities_query.filter(Entity.entity_id == entity_id)
    entities = entities_query.all()

    entity_trends: Dict[str, Any] = {}

    for ent in entities:
        eid = ent.entity_id
        period_metrics = []

        for p in periods:
            pid = p.period_id
            alerts = db.query(Alert).filter(
                Alert.entity_id == eid,
                Alert.assessment_period_id == pid
            ).all()

            total_alerts = len(alerts)
            declared_assets = ent.monitored_asset_count or 1
            active_assets = len({a.asset_id for a in alerts if a.asset_id})
            coverage_gap = max(0.0, ((declared_assets - active_assets) / declared_assets) * 100.0)
            evidence_rate = (sum(1 for a in alerts if a.evidence_present) / max(total_alerts, 1)) * 100.0

            findings_count = db.query(Finding).filter(
                Finding.entity_id == eid,
                Finding.assessment_period_id == pid
            ).count()

            period_metrics.append({
                "period_id": pid,
                "period_name": p.name,
                "total_alerts": total_alerts,
                "coverage_gap_pct": round(coverage_gap, 1),
                "evidence_rate_pct": round(evidence_rate, 1),
                "findings_count": findings_count
            })

        # Calculate drift between first and last period
        deterioration_signals = []
        if len(period_metrics) >= 2:
            first = period_metrics[0]
            last = period_metrics[-1]

            gap_delta = last["coverage_gap_pct"] - first["coverage_gap_pct"]
            if gap_delta >= 15.0:
                deterioration_signals.append({
                    "drift_type": "MONITORING_COVERAGE_DETERIORATION",
                    "severity": "HIGH",
                    "first_period": f"{first['period_id']} ({first['coverage_gap_pct']}%)",
                    "latest_period": f"{last['period_id']} ({last['coverage_gap_pct']}%)",
                    "delta": f"+{round(gap_delta, 1)}% blind spot expansion",
                    "explanation": f"Telemetry coverage on monitored assets has steadily eroded over time from {first['period_id']} to {last['period_id']}."
                })

            ev_delta = first["evidence_rate_pct"] - last["evidence_rate_pct"]
            if ev_delta >= 20.0:
                deterioration_signals.append({
                    "drift_type": "INVESTIGATION_QUALITY_DRIFT",
                    "severity": "MEDIUM",
                    "first_period": f"{first['period_id']} ({first['evidence_rate_pct']}%)",
                    "latest_period": f"{last['period_id']} ({last['evidence_rate_pct']}%)",
                    "delta": f"-{round(ev_delta, 1)}% evidence drop",
                    "explanation": f"Investigation documentation and evidence attachment rates have significantly deteriorated."
                })

        entity_trends[eid] = {
            "entity_name": ent.name,
            "period_metrics": period_metrics,
            "deterioration_signals": deterioration_signals,
            "has_deterioration": len(deterioration_signals) > 0
        }

    return {
        "status": "COMPLETED",
        "periods_analyzed": period_ids,
        "entity_trends": entity_trends
    }
