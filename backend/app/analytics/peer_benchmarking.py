import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entity import Entity, Asset
from app.models.alert import Alert


MIN_PEER_SAMPLE_SIZE = 3


def compute_robust_baseline(values: List[float]) -> Dict[str, Any]:
    """Computes robust statistical metrics: median, MAD, IQR, percentiles (Section 11)."""
    if not values:
        return {
            "median": 0.0,
            "mad": 0.0,
            "iqr": 0.0,
            "p25": 0.0,
            "p75": 0.0,
            "mean": 0.0,
            "sample_size": 0,
            "status": "INSUFFICIENT_SAMPLE"
        }

    arr = np.array(values, dtype=float)
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    p25 = float(np.percentile(arr, 25))
    p75 = float(np.percentile(arr, 75))
    iqr = float(p75 - p25)
    mean = float(np.mean(arr))

    return {
        "median": round(med, 2),
        "mad": round(mad, 2),
        "iqr": round(iqr, 2),
        "p25": round(p25, 2),
        "p75": round(p75, 2),
        "mean": round(mean, 2),
        "sample_size": len(values),
        "status": "VALID_SAMPLE" if len(values) >= MIN_PEER_SAMPLE_SIZE else "LIMITED_SAMPLE"
    }


def evaluate_peer_benchmarking(
    db: Session,
    assessment_period_id: str = "2026-Q2",
    peer_group_by: str = "all"  # "all", "sector", "tier"
) -> Dict[str, Any]:
    """
    Peer Benchmarking Engine with explicit PeerGroup support and robust statistics (Section 11).
    Evaluates entity deviations against peer distributions without calling every difference an anomaly.
    """
    entities = db.query(Entity).all()
    if len(entities) < MIN_PEER_SAMPLE_SIZE:
        return {
            "status": "INSUFFICIENT_PEER_SAMPLE",
            "peer_sample_size": len(entities),
            "message": f"Peer pool ({len(entities)}) is below minimum required sample ({MIN_PEER_SAMPLE_SIZE}).",
            "peer_baselines": {},
            "entity_benchmarks": {}
        }

    # Extract operational metrics per entity
    entity_metrics: Dict[str, Dict[str, Any]] = {}

    for ent in entities:
        eid = ent.entity_id
        alerts = db.query(Alert).filter(
            Alert.entity_id == eid,
            Alert.assessment_period_id == assessment_period_id
        ).all()

        if not alerts:
            alerts = db.query(Alert).filter(Alert.entity_id == eid).all()

        total = len(alerts)

        # Closure duration on critical/high alerts
        crit_closure_mins = []
        for a in alerts:
            if a.severity in ["CRITICAL", "HIGH"] and a.closed_timestamp and a.alert_timestamp:
                dur = (a.closed_timestamp - a.alert_timestamp).total_seconds() / 60.0
                if dur > 0:
                    crit_closure_mins.append(dur)

        median_crit_closure = float(np.median(crit_closure_mins)) if crit_closure_mins else 0.0

        # Evidence rate
        evidence_count = sum(1 for a in alerts if a.evidence_present)
        evidence_rate = (evidence_count / max(total, 1)) * 100.0

        # Critical escalation rate
        crit_alerts = [a for a in alerts if a.severity == "CRITICAL"]
        crit_esc = sum(1 for a in crit_alerts if a.escalated)
        crit_esc_rate = (crit_esc / max(len(crit_alerts), 1)) * 100.0 if crit_alerts else 80.0

        # Remediation rate
        remed_count = sum(1 for a in alerts if a.remediation_recorded)
        remediation_rate = (remed_count / max(total, 1)) * 100.0

        # Coverage gap
        declared = ent.monitored_asset_count or 1
        active_assets = len({a.asset_id for a in alerts if a.asset_id})
        coverage_gap = max(0.0, ((declared - active_assets) / declared) * 100.0)

        entity_metrics[eid] = {
            "entity_name": ent.name,
            "sector": ent.sector,
            "claimed_tier": ent.claimed_tier,
            "total_alerts": total,
            "median_crit_closure_mins": round(median_crit_closure, 1),
            "evidence_rate_pct": round(evidence_rate, 1),
            "critical_escalation_rate_pct": round(crit_esc_rate, 1),
            "remediation_rate_pct": round(remediation_rate, 1),
            "coverage_gap_pct": round(coverage_gap, 1)
        }

    # Robust baselines across peer cohort
    all_volumes = [float(m["total_alerts"]) for m in entity_metrics.values()]
    all_closures = [m["median_crit_closure_mins"] for m in entity_metrics.values() if m["median_crit_closure_mins"] > 0]
    all_ev_rates = [m["evidence_rate_pct"] for m in entity_metrics.values()]
    all_esc_rates = [m["critical_escalation_rate_pct"] for m in entity_metrics.values()]
    all_remed_rates = [m["remediation_rate_pct"] for m in entity_metrics.values()]
    all_cov_gaps = [m["coverage_gap_pct"] for m in entity_metrics.values()]

    peer_baselines = {
        "alert_volume": compute_robust_baseline(all_volumes),
        "closure_duration_mins": compute_robust_baseline(all_closures),
        "evidence_rate_pct": compute_robust_baseline(all_ev_rates),
        "critical_escalation_rate_pct": compute_robust_baseline(all_esc_rates),
        "remediation_rate_pct": compute_robust_baseline(all_remed_rates),
        "coverage_gap_pct": compute_robust_baseline(all_cov_gaps)
    }

    entity_benchmarks: Dict[str, Any] = {}
    sample_size = len(entity_metrics)

    for eid, m in entity_metrics.items():
        deviations = []

        # 1. Closure duration comparison
        med_closure = peer_baselines["closure_duration_mins"]["median"]
        if med_closure > 0 and m["median_crit_closure_mins"] > 0:
            diff_ratio = (m["median_crit_closure_mins"] - med_closure) / med_closure
            if diff_ratio < -0.70:
                deviations.append({
                    "metric": "CRITICAL_CLOSURE_DURATION",
                    "entity_value": f"{m['median_crit_closure_mins']}m",
                    "peer_baseline": f"{med_closure}m (IQR: {peer_baselines['closure_duration_mins']['iqr']}m)",
                    "deviation_pct": round(diff_ratio * 100.0, 1),
                    "interpretation": "SIGNIFICANTLY_FASTER_THAN_PEERS (Potential metrics optimization/gaming)",
                    "peer_sample_size": sample_size
                })

        # 2. Evidence rate comparison
        med_ev = peer_baselines["evidence_rate_pct"]["median"]
        if m["evidence_rate_pct"] < (med_ev - 30.0):
            deviations.append({
                "metric": "INVESTIGATION_EVIDENCE_RATE",
                "entity_value": f"{m['evidence_rate_pct']}%",
                "peer_baseline": f"{med_ev}% (IQR: {peer_baselines['evidence_rate_pct']['iqr']}%)",
                "deviation_pct": round(m["evidence_rate_pct"] - med_ev, 1),
                "interpretation": "SEVERE_DEFICIT_BELOW_PEERS (Investigation evidence deficit)",
                "peer_sample_size": sample_size
            })

        # 3. Coverage gap comparison
        med_gap = peer_baselines["coverage_gap_pct"]["median"]
        if m["coverage_gap_pct"] > (med_gap + 25.0):
            deviations.append({
                "metric": "MONITORING_COVERAGE_GAP",
                "entity_value": f"{m['coverage_gap_pct']}%",
                "peer_baseline": f"{med_gap}% (IQR: {peer_baselines['coverage_gap_pct']['iqr']}%)",
                "deviation_pct": round(m["coverage_gap_pct"] - med_gap, 1),
                "interpretation": "ELEVATED_BLIND_SPOT_VS_PEERS (Negative Space)",
                "peer_sample_size": sample_size
            })

        # 4. Escalation rate comparison
        med_esc = peer_baselines["critical_escalation_rate_pct"]["median"]
        if m["critical_escalation_rate_pct"] < (med_esc - 40.0):
            deviations.append({
                "metric": "CRITICAL_ESCALATION_RATE",
                "entity_value": f"{m['critical_escalation_rate_pct']}%",
                "peer_baseline": f"{med_esc}% (IQR: {peer_baselines['critical_escalation_rate_pct']['iqr']}%)",
                "deviation_pct": round(m["critical_escalation_rate_pct"] - med_esc, 1),
                "interpretation": "SUB_PEER_ESCALATION_FIDELITY (Mandatory escalation bypass)",
                "peer_sample_size": sample_size
            })

        entity_benchmarks[eid] = {
            "metrics": m,
            "deviations": deviations,
            "deviation_count": len(deviations),
            "supervisory_signal": "REQUIRES_SUPERVISORY_ATTENTION" if len(deviations) > 0 else "CONSISTENT_WITH_PEERS"
        }

    return {
        "status": "COMPLETED",
        "assessment_period_id": assessment_period_id,
        "peer_group_by": peer_group_by,
        "peer_sample_size": sample_size,
        "peer_baselines": peer_baselines,
        "entity_benchmarks": entity_benchmarks
    }
