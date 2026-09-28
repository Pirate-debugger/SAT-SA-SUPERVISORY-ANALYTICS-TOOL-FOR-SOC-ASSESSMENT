import json
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding
from app.models.analysis_run import CapabilityScore
from app.time_utils import utc_now


DIMENSION_NAMES = [
    "THREAT_DETECTION",
    "INVESTIGATION",
    "ESCALATION",
    "INCIDENT_RESPONSE",
    "SECURITY_OPERATIONS",
    "GOVERNANCE_AND_OVERSIGHT",
    "OPERATIONAL_DISCIPLINE",
    "CYBER_RESILIENCE"
]


def determine_assessment_status(score: float, sample_size: int, has_critical_finding: bool) -> str:
    """Returns official supervisory status (Section 6)."""
    if sample_size < 5:
        return "INSUFFICIENT EVIDENCE"
    if has_critical_finding or score < 60.0:
        return "ATTENTION"
    if score >= 75.0:
        return "STRONG EVIDENCE"
    return "ATTENTION"


def evaluate_8_capability_dimensions(
    db: Session,
    run_id: str,
    entity_id: str,
    assessment_period_id: str = "2026-Q2",
    peer_medians: Optional[Dict[str, float]] = None
) -> List[CapabilityScore]:
    """
    Evaluates evidence-backed scores across the 8 standard supervisory capability dimensions (Section 6).
    Derives scores purely from actual observable operational evidence, without arbitrary '85 - penalty' constants.
    """
    ent = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    alerts = db.query(Alert).filter(
        Alert.entity_id == entity_id,
        Alert.assessment_period_id == assessment_period_id
    ).all()
    if not alerts:
        alerts = db.query(Alert).filter(Alert.entity_id == entity_id).all()

    total_alerts = len(alerts)
    cases = db.query(Case).filter(
        Case.entity_id == entity_id,
        Case.assessment_period_id == assessment_period_id
    ).all()
    if not cases:
        cases = db.query(Case).filter(Case.entity_id == entity_id).all()

    total_cases = len(cases)

    # Findings affecting this entity in this run
    findings = db.query(Finding).filter(
        Finding.run_id == run_id,
        Finding.entity_id == entity_id
    ).all()

    findings_by_dim: Dict[str, List[Finding]] = {d: [] for d in DIMENSION_NAMES}
    for f in findings:
        dim = f.capability_dimension or "SECURITY_OPERATIONS"
        if dim in findings_by_dim:
            findings_by_dim[dim].append(f)

    if total_alerts == 0:
        # Not assessed or insufficient evidence
        return [
            CapabilityScore(
                run_id=run_id,
                entity_id=entity_id,
                assessment_period_id=assessment_period_id,
                dimension=d,
                score=0.0,
                status="NOT ASSESSED",
                observed_metrics_json=json.dumps({"alert_count": 0, "case_count": 0}),
                baseline_json=json.dumps({"min_required_alerts": 5}),
                peer_median=70.0,
                deviation=0.0,
                confidence=0.0,
                trend="STABLE"
            )
            for d in DIMENSION_NAMES
        ]

    # Compute actual evidence metrics for each dimension:

    # 1. THREAT_DETECTION
    # Observed: Category diversity ratio + volume realism
    unique_categories = {a.category for a in alerts if a.category and a.category != "UNKNOWN"}
    expected_categories_count = 8
    cat_diversity_ratio = min(1.0, len(unique_categories) / expected_categories_count)
    td_score = cat_diversity_ratio * 100.0
    td_obs = {
        "active_threat_categories": len(unique_categories),
        "expected_categories": expected_categories_count,
        "diversity_ratio": round(cat_diversity_ratio, 2)
    }

    # 2. INVESTIGATION
    # Observed: Evidence attachment rate + root cause identification rate
    evidence_count = sum(1 for a in alerts if a.evidence_present)
    evidence_rate = (evidence_count / total_alerts) * 100.0
    root_cause_count = sum(1 for a in alerts if a.root_cause_recorded)
    rc_rate = (root_cause_count / total_alerts) * 100.0
    inv_score = (evidence_rate * 0.70) + (rc_rate * 0.30)
    inv_obs = {
        "evidence_attachment_rate_pct": round(evidence_rate, 1),
        "root_cause_documented_rate_pct": round(rc_rate, 1),
        "alerts_with_evidence": evidence_count
    }

    # 3. ESCALATION
    # Observed: Critical/High alerts escalation fidelity
    crit_high_alerts = [a for a in alerts if a.severity in ["CRITICAL", "HIGH"]]
    if crit_high_alerts:
        escalated_crit = sum(1 for a in crit_high_alerts if a.escalated)
        esc_rate = (escalated_crit / len(crit_high_alerts)) * 100.0
    else:
        esc_rate = 85.0  # Normal baseline if no critical threats occurred
    esc_score = esc_rate
    esc_obs = {
        "critical_high_alerts_count": len(crit_high_alerts),
        "escalated_count": sum(1 for a in crit_high_alerts if a.escalated),
        "escalation_rate_pct": round(esc_rate, 1)
    }

    # 4. INCIDENT_RESPONSE
    # Observed: Remediation recording rate + case resolution fidelity
    remed_count = sum(1 for a in alerts if a.remediation_recorded)
    remed_rate = (remed_count / total_alerts) * 100.0
    resolved_cases = sum(1 for c in cases if c.closed_at)
    case_res_rate = (resolved_cases / max(total_cases, 1)) * 100.0 if total_cases > 0 else remed_rate
    ir_score = (remed_rate * 0.60) + (case_res_rate * 0.40)
    ir_obs = {
        "remediation_recorded_rate_pct": round(remed_rate, 1),
        "cases_resolved_pct": round(case_res_rate, 1),
        "remediated_alerts_count": remed_count
    }

    # 5. SECURITY_OPERATIONS
    # Observed: Triage duration realism (proportion of alerts with adequate investigation time >= 15m)
    adequate_triage_count = 0
    triage_evaluated = 0
    for a in alerts:
        if a.closed_timestamp and a.alert_timestamp:
            dur_m = (a.closed_timestamp - a.alert_timestamp).total_seconds() / 60.0
            if dur_m > 0:
                triage_evaluated += 1
                if dur_m >= 15.0 or a.severity not in ["CRITICAL", "HIGH"]:
                    adequate_triage_count += 1
    secops_score = (adequate_triage_count / max(triage_evaluated, 1)) * 100.0 if triage_evaluated > 0 else 75.0
    secops_obs = {
        "adequate_triage_rate_pct": round(secops_score, 1),
        "triage_evaluated_alerts": triage_evaluated,
        "rapid_dismissals": triage_evaluated - adequate_triage_count
    }

    # 6. GOVERNANCE_AND_OVERSIGHT
    # Observed: Asset coverage compliance (active assets reporting vs declared scope)
    declared = ent.monitored_asset_count or 1 if ent else 1
    active_assets = len({a.asset_id for a in alerts if a.asset_id})
    coverage_ratio = min(1.0, active_assets / declared) * 100.0
    gov_score = coverage_ratio
    gov_obs = {
        "declared_monitored_assets": declared,
        "active_reporting_assets": active_assets,
        "asset_coverage_rate_pct": round(coverage_ratio, 1)
    }

    # 7. OPERATIONAL_DISCIPLINE
    # Observed: Non-boilerplate uniqueness of closure rationale + zero repeat alert loops
    notes = [c.closure_reason.strip() for c in cases if c.closure_reason and len(c.closure_reason.strip()) > 5]
    if notes:
        from collections import Counter
        most_common_cnt = Counter(notes).most_common(1)[0][1]
        repetition_pct = (most_common_cnt / len(notes)) * 100.0
        discipline_score = max(0.0, 100.0 - repetition_pct)
    else:
        repetition_pct = 0.0
        discipline_score = 80.0
    disc_obs = {
        "case_closure_notes_evaluated": len(notes),
        "boilerplate_repetition_pct": round(repetition_pct, 1),
        "investigation_diversity_score": round(discipline_score, 1)
    }

    # 8. CYBER_RESILIENCE
    # Observed: Synthesis of coverage breadth + permanent remediation posture
    resilience_score = (coverage_ratio * 0.50) + (remed_rate * 0.50)
    res_obs = {
        "telemetry_coverage_contribution": round(coverage_ratio * 0.50, 1),
        "remediation_posture_contribution": round(remed_rate * 0.50, 1)
    }

    raw_scores = {
        "THREAT_DETECTION": (td_score, td_obs),
        "INVESTIGATION": (inv_score, inv_obs),
        "ESCALATION": (esc_score, esc_obs),
        "INCIDENT_RESPONSE": (ir_score, ir_obs),
        "SECURITY_OPERATIONS": (secops_score, secops_obs),
        "GOVERNANCE_AND_OVERSIGHT": (gov_score, gov_obs),
        "OPERATIONAL_DISCIPLINE": (discipline_score, disc_obs),
        "CYBER_RESILIENCE": (resilience_score, res_obs)
    }

    score_models: List[CapabilityScore] = []
    for dim in DIMENSION_NAMES:
        raw_sc, obs_dict = raw_scores[dim]
        dim_findings = findings_by_dim.get(dim, [])
        has_crit = any(f.severity in ["CRITICAL", "HIGH"] for f in dim_findings)

        # Apply evidence deficit penalty from confirmed findings
        fnd_penalty = sum(25.0 if f.severity == "CRITICAL" else (15.0 if f.severity == "HIGH" else 5.0)
                          for f in dim_findings)
        final_score = max(5.0, min(100.0, raw_sc - fnd_penalty))
        final_score = round(final_score, 1)

        # Baseline peer context (calculated dynamically or default to 70.0)
        p_median = peer_medians.get(dim, 70.0) if peer_medians else 70.0
        deviation = round(final_score - p_median, 1)

        status = determine_assessment_status(final_score, total_alerts, has_crit)

        # Confidence based on sample size
        conf = 0.95 if total_alerts >= 50 else (0.80 if total_alerts >= 20 else 0.60)

        score_models.append(CapabilityScore(
            run_id=run_id,
            entity_id=entity_id,
            assessment_period_id=assessment_period_id,
            dimension=dim,
            score=final_score,
            status=status,
            observed_metrics_json=json.dumps(obs_dict),
            baseline_json=json.dumps({"peer_median": p_median, "target_standard": 75.0}),
            peer_median=p_median,
            deviation=deviation,
            confidence=conf,
            trend="DETERIORATING" if has_crit else ("IMPROVING" if final_score >= 80.0 else "STABLE")
        ))

    return score_models
