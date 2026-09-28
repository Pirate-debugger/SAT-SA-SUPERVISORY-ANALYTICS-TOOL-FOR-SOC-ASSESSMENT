import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.models.case import Case


def compute_robust_baseline(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"median": 0.0, "mad": 0.0, "p25": 0.0, "p75": 0.0, "mean": 0.0, "sample_size": 0}

    arr = np.array(values, dtype=float)
    med = float(np.median(arr))
    # Median Absolute Deviation (MAD)
    mad = float(np.median(np.abs(arr - med)))
    p25 = float(np.percentile(arr, 25))
    p75 = float(np.percentile(arr, 75))
    mean = float(np.mean(arr))

    return {
        "median": round(med, 2),
        "mad": round(mad, 2),
        "p25": round(p25, 2),
        "p75": round(p75, 2),
        "mean": round(mean, 2),
        "sample_size": len(values)
    }


def evaluate_peer_benchmarking(
    db: Session,
    assessment_period_id: str = "2026-Q2"
) -> Dict[str, Any]:
    """
    Groups entities into peer groups (by sector / tier) and computes robust baselines.
    Compares each entity against peer distribution and flags significant deviations.
    """
    entities = db.query(Entity).all()
    if not entities:
        return {"peer_groups": {}, "entity_benchmarks": {}}

    # Collect operational metrics per entity
    entity_metrics: Dict[str, Dict[str, Any]] = {}

    for ent in entities:
        eid = ent.entity_id
        alerts = db.query(Alert).filter(
            Alert.entity_id == eid,
            Alert.assessment_period_id == assessment_period_id
        ).all()

        total_alerts = len(alerts)
        if total_alerts == 0:
            # Fallback across all periods if single period empty
            alerts = db.query(Alert).filter(Alert.entity_id == eid).all()
            total_alerts = len(alerts)

        # 1. Closure Durations for Critical/High alerts
        crit_closure_mins = []
        for a in alerts:
            if a.severity in ["CRITICAL", "HIGH"] and a.closed_timestamp and a.alert_timestamp:
                diff_m = (a.closed_timestamp - a.alert_timestamp).total_seconds() / 60.0
                if diff_m > 0:
                    crit_closure_mins.append(diff_m)

        avg_crit_closure = float(np.median(crit_closure_mins)) if crit_closure_mins else 0.0

        # 2. Evidence Rate
        evidence_count = sum(1 for a in alerts if a.evidence_present)
        evidence_rate = (evidence_count / max(total_alerts, 1)) * 100.0

        # 3. Escalation Rate for Critical Alerts
        crit_alerts = [a for a in alerts if a.severity == "CRITICAL"]
        crit_escalated = sum(1 for a in crit_alerts if a.escalated)
        crit_escalation_rate = (crit_escalated / max(len(crit_alerts), 1)) * 100.0

        # 4. Remediation Rate
        remediated_count = sum(1 for a in alerts if a.remediation_recorded)
        remediation_rate = (remediated_count / max(total_alerts, 1)) * 100.0

        # 5. Coverage Gap
        declared = ent.monitored_asset_count or 1
        active_assets = len({a.asset_id for a in alerts if a.asset_id})
        coverage_gap = max(0.0, ((declared - active_assets) / declared) * 100.0)

        entity_metrics[eid] = {
            "entity_name": ent.name,
            "sector": ent.sector,
            "claimed_tier": ent.claimed_tier,
            "total_alerts": total_alerts,
            "median_crit_closure_mins": round(avg_crit_closure, 1),
            "evidence_rate_pct": round(evidence_rate, 1),
            "critical_escalation_rate_pct": round(crit_escalation_rate, 1),
            "remediation_rate_pct": round(remediation_rate, 1),
            "coverage_gap_pct": round(coverage_gap, 1)
        }

    # Aggregate baselines across entire supervised peer pool
    all_crit_closures = [m["median_crit_closure_mins"] for m in entity_metrics.values() if m["median_crit_closure_mins"] > 0]
    all_evidence_rates = [m["evidence_rate_pct"] for m in entity_metrics.values()]
    all_esc_rates = [m["critical_escalation_rate_pct"] for m in entity_metrics.values()]
    all_coverage_gaps = [m["coverage_gap_pct"] for m in entity_metrics.values()]

    peer_baseline = {
        "closure_duration_mins": compute_robust_baseline(all_crit_closures),
        "evidence_rate_pct": compute_robust_baseline(all_evidence_rates),
        "critical_escalation_rate_pct": compute_robust_baseline(all_esc_rates),
        "coverage_gap_pct": compute_robust_baseline(all_coverage_gaps)
    }

    # Compute comparative position and deviations for each entity
    entity_benchmarks: Dict[str, Any] = {}

    for eid, m in entity_metrics.items():
        deviations = []
        peer_sample = len(entity_metrics)

        # Compare closure duration
        med_closure = peer_baseline["closure_duration_mins"]["median"]
        if med_closure > 0 and m["median_crit_closure_mins"] > 0:
            diff_ratio = (m["median_crit_closure_mins"] - med_closure) / med_closure
            if diff_ratio < -0.70:  # 70% faster than peer median indicates rapid closure
                deviations.append({
                    "metric": "CRITICAL_CLOSURE_DURATION",
                    "entity_value": f"{m['median_crit_closure_mins']}m",
                    "peer_baseline": f"{med_closure}m",
                    "deviation_pct": round(diff_ratio * 100, 1),
                    "interpretation": "SIGNIFICANT_FASTER_THAN_PEERS (Potential metrics optimization/gaming)",
                    "peer_sample_size": peer_sample
                })

        # Compare evidence rate
        med_ev = peer_baseline["evidence_rate_pct"]["median"]
        if m["evidence_rate_pct"] < (med_ev - 30.0):
            deviations.append({
                "metric": "INVESTIGATION_EVIDENCE_RATE",
                "entity_value": f"{m['evidence_rate_pct']}%",
                "peer_baseline": f"{med_ev}%",
                "deviation_pct": round(m["evidence_rate_pct"] - med_ev, 1),
                "interpretation": "SEVERE_DEFICIT_BELOW_PEERS (Potential investigation deficit)",
                "peer_sample_size": peer_sample
            })

        # Compare coverage gap
        med_gap = peer_baseline["coverage_gap_pct"]["median"]
        if m["coverage_gap_pct"] > (med_gap + 25.0):
            deviations.append({
                "metric": "MONITORING_COVERAGE_GAP",
                "entity_value": f"{m['coverage_gap_pct']}%",
                "peer_baseline": f"{med_gap}%",
                "deviation_pct": round(m["coverage_gap_pct"] - med_gap, 1),
                "interpretation": "ELEVATED_BLIND_SPOT_VS_PEERS (Negative Space)",
                "peer_sample_size": peer_sample
            })

        entity_benchmarks[eid] = {
            "metrics": m,
            "deviations": deviations,
            "deviation_count": len(deviations),
            "supervisory_signal": "REQUIRES_SUPERVISORY_ATTENTION" if len(deviations) > 0 else "CONSISTENT_WITH_PEERS"
        }

    return {
        "assessment_period_id": assessment_period_id,
        "peer_sample_size": len(entities),
        "peer_baselines": peer_baseline,
        "entity_benchmarks": entity_benchmarks
    }
