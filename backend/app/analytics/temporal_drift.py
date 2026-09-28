import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.entity import Entity, AssessmentPeriod
from app.models.alert import Alert
from app.models.finding import Finding


def evaluate_temporal_drift(db: Session, entity_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes rigorous temporal drift, slopes, persistence, step-changes, and volatility across all periods (Section 13).
    Does NOT only compare first and last period.
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

            findings = db.query(Finding).filter(
                Finding.entity_id == eid,
                Finding.assessment_period_id == pid
            ).all()

            if total_alerts == 0 and len(findings) == 0:
                continue

            period_metrics.append({
                "period_id": pid,
                "period_name": p.name,
                "total_alerts": total_alerts,
                "coverage_gap_pct": round(coverage_gap, 1),
                "evidence_rate_pct": round(evidence_rate, 1),
                "findings_count": len(findings),
                "finding_types": list({f.finding_type for f in findings})
            })

        # Multi-period analysis (slopes, step changes, persistence)
        n_periods = len(period_metrics)
        if n_periods < 2:
            continue
        coverage_series = [pm["coverage_gap_pct"] for pm in period_metrics]
        evidence_series = [pm["evidence_rate_pct"] for pm in period_metrics]
        findings_series = [float(pm["findings_count"]) for pm in period_metrics]

        # Calculate slope: delta y / delta t
        x_indices = np.arange(n_periods)
        coverage_slope = float(np.polyfit(x_indices, coverage_series, 1)[0]) if n_periods >= 2 else 0.0
        evidence_slope = float(np.polyfit(x_indices, evidence_series, 1)[0]) if n_periods >= 2 else 0.0

        # Step changes
        step_changes = []
        for i in range(1, n_periods):
            p_prev = period_metrics[i - 1]
            p_curr = period_metrics[i]
            cov_delta = p_curr["coverage_gap_pct"] - p_prev["coverage_gap_pct"]
            ev_delta = p_curr["evidence_rate_pct"] - p_prev["evidence_rate_pct"]
            step_changes.append({
                "from_period": p_prev["period_id"],
                "to_period": p_curr["period_id"],
                "coverage_gap_delta": round(cov_delta, 1),
                "evidence_rate_delta": round(ev_delta, 1)
            })

        # Persistence: finding types appearing in multiple periods
        all_types = set()
        for pm in period_metrics:
            all_types.update(pm["finding_types"])

        persistent_weaknesses = []
        newly_emerging_weaknesses = []
        resolved_weaknesses = []

        latest_types = set(period_metrics[-1]["finding_types"])
        earlier_types = set()
        for pm in period_metrics[:-1]:
            earlier_types.update(pm["finding_types"])

        for ftype in all_types:
            occurrence_count = sum(1 for pm in period_metrics if ftype in pm["finding_types"])
            if occurrence_count >= 2:
                persistent_weaknesses.append(ftype)

        for ftype in latest_types:
            if ftype not in earlier_types:
                newly_emerging_weaknesses.append(ftype)

        for ftype in earlier_types:
            if ftype not in latest_types:
                resolved_weaknesses.append(ftype)

        # Deterioration signals
        deterioration_signals = []
        if coverage_slope >= 5.0:
            deterioration_signals.append({
                "drift_type": "SUSTAINED_MONITORING_COVERAGE_DETERIORATION",
                "severity": "HIGH",
                "slope": round(coverage_slope, 2),
                "summary": f"Coverage gap is steadily widening across periods (slope: +{coverage_slope:.1f}% per cycle).",
                "series": coverage_series
            })

        if evidence_slope <= -6.0:
            deterioration_signals.append({
                "drift_type": "SUSTAINED_INVESTIGATION_QUALITY_DETERIORATION",
                "severity": "HIGH",
                "slope": round(evidence_slope, 2),
                "summary": f"Investigation evidence rate is declining consistently (slope: {evidence_slope:.1f}% per cycle).",
                "series": evidence_series
            })

        # Volatility (standard deviation of findings)
        findings_volatility = round(float(np.std(findings_series)), 2)

        entity_trends[eid] = {
            "entity_name": ent.name,
            "period_metrics": period_metrics,
            "step_changes": step_changes,
            "coverage_slope": round(coverage_slope, 2),
            "evidence_slope": round(evidence_slope, 2),
            "findings_volatility": findings_volatility,
            "persistent_weaknesses": persistent_weaknesses,
            "newly_emerging_weaknesses": newly_emerging_weaknesses,
            "resolved_weaknesses": resolved_weaknesses,
            "deterioration_signals": deterioration_signals,
            "overall_trajectory": (
                "DETERIORATING" if len(deterioration_signals) > 0 or coverage_slope > 4.0
                else ("IMPROVING" if coverage_slope < -4.0 and evidence_slope > 4.0 else "STABLE")
            )
        }

    return {
        "status": "COMPLETED",
        "periods_analyzed": period_ids,
        "entity_trends": entity_trends
    }
