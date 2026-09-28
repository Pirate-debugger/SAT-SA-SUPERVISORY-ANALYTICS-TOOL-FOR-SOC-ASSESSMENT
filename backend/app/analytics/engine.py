import time
import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import RULESET_VERSION, ANALYTICS_VERSION, MODEL_VERSION
from app.models.entity import Entity, Asset, AssessmentPeriod
from app.models.alert import Alert
from app.models.case import Case
from app.models.analysis_run import AnalysisRun, CapabilityScore
from app.models.finding import Finding, FindingEvidenceLink
from app.models.audit import AuditLog, ReviewItem
from app.analytics.execution_gaps import evaluate_execution_gaps_for_entity
from app.analytics.negative_space import evaluate_negative_space_for_entity
from app.analytics.capability_dimensions import evaluate_8_capability_dimensions, DIMENSION_NAMES
from app.analytics.peer_benchmarking import evaluate_peer_benchmarking
from app.analytics.anomaly_engine import detect_operational_anomalies
from app.ingestion.pipeline import append_audit_event
from app.time_utils import utc_now


def calculate_supervisory_attention_indicator(
    findings: Any,
    capability_scores: Any = None,
    peer_deviations: Any = 0,
    anomalies_count: Any = 0
) -> Tuple[str, float, Dict[str, float]]:
    """
    Computes explainable Supervisory Attention Indicator (SAI) (Section 14).
    Returns (level: CRITICAL/HIGH/MODERATE/LOW, score: 0-100, component_contributions)
    Deterministic, reproducible, evidence-backed.
    Supports either model instances or dictionary summaries.
    """
    gap_score = 0.0
    neg_score = 0.0
    anom_score = 0.0
    cap_deficits: Dict[str, float] = {}

    # 1. Process Findings (List of Finding objects or dict summary)
    if isinstance(findings, dict):
        gap_score = float(findings.get("execution_gaps_count", 0)) * 8.0 + float(findings.get("critical_findings_count", 0)) * 12.0
        neg_score = float(findings.get("negative_space_count", 0)) * 10.0
        anom_score = float(findings.get("anomalies_count", 0)) * 5.0
    elif isinstance(findings, list):
        for f in findings:
            cat = getattr(f, "category", "")
            sev = getattr(f, "severity", "LOW")
            weight = 30.0 if sev == "CRITICAL" else (18.0 if sev == "HIGH" else 8.0)
            if cat == "EXECUTION_GAP":
                gap_score += weight
            elif cat == "NEGATIVE_SPACE":
                neg_score += (25.0 if sev == "CRITICAL" else 15.0)
            elif cat == "ANOMALY":
                anom_score += (15.0 if sev == "CRITICAL" else (10.0 if sev == "HIGH" else 5.0))

    # 2. Process Capability Scores (List of CapabilityScore or dict)
    if isinstance(capability_scores, dict):
        for dim, val in capability_scores.items():
            sc = val.get("score") if isinstance(val, dict) else val
            if sc is not None and sc < 75.0:
                deficit = round((75.0 - sc) * 0.4, 1)
                dim_name = dim.replace("_", " ").title()
                cap_deficits[dim_name] = deficit
    elif isinstance(capability_scores, list):
        for cs in capability_scores:
            sc = getattr(cs, "score", None)
            dim = getattr(cs, "dimension", "")
            if sc is not None and sc < 75.0:
                deficit = round((75.0 - sc) * 0.4, 1)
                dim_name = dim.replace("_", " ").title()
                cap_deficits[dim_name] = deficit

    # 3. Peer Deviations
    if isinstance(peer_deviations, list):
        peer_penalty = min(20.0, float(len(peer_deviations)) * 8.0)
    else:
        peer_penalty = min(20.0, float(peer_deviations or 0) * 8.0)

    # 4. Anomalies / Temporal Profile
    temporal_penalty = 0.0
    if isinstance(anomalies_count, dict):
        # Passed temporal profile
        t_data = anomalies_count
        persistence = 0
        if "coverage_trend" in t_data and isinstance(t_data["coverage_trend"], dict):
            persistence = t_data["coverage_trend"].get("persistence", 0)
        temporal_penalty = float(persistence) * 3.5
    else:
        anom_score = max(anom_score, min(15.0, float(anomalies_count or 0) * 5.0))

    cap_deficit_total = sum(cap_deficits.values())
    total_score = gap_score + neg_score + anom_score + cap_deficit_total + peer_penalty + temporal_penalty
    total_score = min(100.0, max(0.0, round(total_score, 1)))

    if total_score >= 60.0:
        level = "CRITICAL"
    elif total_score >= 40.0:
        level = "HIGH"
    elif total_score >= 20.0:
        level = "MODERATE"
    else:
        level = "LOW"

    breakdown = {
        "Execution Gaps": round(gap_score, 1),
        "Negative Space": round(neg_score, 1),
        "Anomalies": round(anom_score, 1),
        "Peer Deviations": round(peer_penalty, 1),
        "Temporal Persistence": round(temporal_penalty, 1),
        "execution_gaps_contribution": round(gap_score, 1),
        "negative_space_contribution": round(neg_score, 1),
        "capability_deficit_contribution": round(cap_deficit_total, 1),
        "peer_deviations_contribution": round(peer_penalty, 1),
        "anomaly_contribution": round(anom_score, 1)
    }
    # Add dimension-specific deficits
    for d_name, d_val in cap_deficits.items():
        breakdown[d_name] = d_val
    if "Investigation" not in breakdown:
        breakdown["Investigation"] = round(cap_deficits.get("Investigation", 0.0), 1)
    if "Escalation" not in breakdown:
        breakdown["Escalation"] = round(cap_deficits.get("Escalation", 0.0), 1)

    return level, total_score, breakdown


def calculate_entity_supervisory_risk(
    findings: List[Finding],
    capability_scores: Optional[List[CapabilityScore]] = None,
    peer_deviations: int = 0,
    anomalies_count: int = 0
) -> Tuple[str, float]:
    """Backward compatibility wrapper returning (level, score)."""
    level, score, _ = calculate_supervisory_attention_indicator(
        findings,
        capability_scores or [],
        peer_deviations,
        anomalies_count
    )
    return level, score


def get_authoritative_entity_metrics(
    db: Session,
    entity_id: str,
    run_id: Optional[str] = None,
    assessment_period_id: str = "2026-Q2"
) -> Dict[str, Any]:
    """
    ONE authoritative source for entity supervisory attention and capability metrics (Section 5).
    Used identically across Dashboard, Entities list, Entity Detail, API, and Reports.
    """
    entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    if not entity:
        return {}

    # If run_id not provided, locate latest completed run for this period
    if not run_id:
        latest_run = db.query(AnalysisRun).filter(
            AnalysisRun.assessment_period_id == assessment_period_id,
            AnalysisRun.is_latest.is_(True),
            AnalysisRun.status == "COMPLETED"
        ).first()
        if not latest_run:
            latest_run = db.query(AnalysisRun).filter(
                AnalysisRun.assessment_period_id == assessment_period_id,
                AnalysisRun.status == "COMPLETED"
            ).order_by(AnalysisRun.timestamp.desc()).first()
        run_id = latest_run.run_id if latest_run else None

    # Fetch run-isolated findings and capability scores
    if run_id:
        findings = db.query(Finding).filter(
            Finding.entity_id == entity_id,
            Finding.run_id == run_id
        ).all()
        cap_scores = db.query(CapabilityScore).filter(
            CapabilityScore.entity_id == entity_id,
            CapabilityScore.run_id == run_id
        ).all()
    else:
        findings = []
        cap_scores = []

    # Ingested records for period
    alerts = db.query(Alert).filter(
        Alert.entity_id == entity_id,
        Alert.assessment_period_id == assessment_period_id
    ).all()
    if not alerts:
        alerts = db.query(Alert).filter(Alert.entity_id == entity_id).all()

    total_alerts = len(alerts)
    cases_cnt = db.query(Case).filter(
        Case.entity_id == entity_id,
        Case.assessment_period_id == assessment_period_id
    ).count()

    # Asset telemetry coverage
    declared_assets = entity.monitored_asset_count or db.query(Asset).filter(Asset.entity_id == entity_id).count() or 1
    active_assets = len({a.asset_id for a in alerts if a.asset_id})
    coverage_gap_pct = max(0.0, ((declared_assets - active_assets) / declared_assets) * 100.0)

    # Finding category breakdown
    gaps_count = sum(1 for f in findings if f.category == "EXECUTION_GAP")
    neg_count = sum(1 for f in findings if f.category == "NEGATIVE_SPACE")
    anom_count = sum(1 for f in findings if f.category == "ANOMALY")

    level, score, breakdown = calculate_supervisory_attention_indicator(
        findings=findings,
        capability_scores=cap_scores,
        peer_deviations=0,
        anomalies_count=anom_count
    )

    primary_concerns = []
    for f in findings:
        if f.severity in ["CRITICAL", "HIGH"] and len(primary_concerns) < 3:
            primary_concerns.append(f.finding_type.replace("_", " ").title())
    if not primary_concerns:
        primary_concerns = ["Operational activity consistent with baseline"]

    return {
        "entity_id": entity_id,
        "name": entity.name,
        "sector": entity.sector,
        "claimed_tier": entity.claimed_tier,
        "monitored_asset_count": declared_assets,
        "active_reporting_assets": active_assets,
        "coverage_gap_pct": round(coverage_gap_pct, 1),
        "total_alerts": total_alerts,
        "total_cases": cases_cnt,
        "execution_gaps_count": gaps_count,
        "negative_space_count": neg_count,
        "anomalies_count": anom_count,
        "supervisory_attention_level": level,
        "supervisory_attention_score": score,
        "supervisory_attention_indicator": score,
        "score_breakdown": breakdown,
        "capability_profile": {cs.dimension: {"score": cs.score, "status": cs.status, "confidence": cs.confidence} for cs in cap_scores},
        "primary_concerns": primary_concerns,
        "run_id": run_id,
        "assessment_period_id": assessment_period_id
    }


def execute_supervisory_analysis_run(
    db: Session,
    entity_ids: Optional[List[str]] = None,
    assessment_period_id: str = "2026-Q2",
    dataset_version: str = "v1.0-offline",
    note: str = "Periodic Supervisory Assessment",
    force_rerun: bool = False
) -> AnalysisRun:
    """
    Executes authoritative supervisory assessment run with strict RUN ISOLATION and IDEMPOTENCY (Section 4).
    Prevents analytical contamination or duplicate active findings from repeated runs.
    """
    start_time = time.time()
    now_utc = utc_now()

    # Compute deterministic config hash for idempotency checking (Section 4)
    # Check alert count to ensure dataset changes trigger new run
    alert_count_in_period = db.query(Alert).filter(Alert.assessment_period_id == assessment_period_id).count()
    config_str = f"{assessment_period_id}:{sorted(entity_ids or [])}:{dataset_version}:{RULESET_VERSION}:{MODEL_VERSION}:{alert_count_in_period}"
    config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]

    # IDEMPOTENCY CHECK: If identical run completed previously and not force_rerun, return it!
    if not force_rerun:
        existing_run = db.query(AnalysisRun).filter(
            AnalysisRun.assessment_period_id == assessment_period_id,
            AnalysisRun.config_hash == config_hash,
            AnalysisRun.status == "COMPLETED"
        ).order_by(AnalysisRun.timestamp.desc()).first()

        if existing_run:
            # Re-ensure it is marked latest and return existing run without inflating findings!
            db.query(AnalysisRun).filter(
                AnalysisRun.assessment_period_id == assessment_period_id,
                AnalysisRun.run_id != existing_run.run_id
            ).update({"is_latest": False})
            existing_run.is_latest = True
            db.commit()
            return existing_run

    run_id = f"RUN-{now_utc.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    # Ensure assessment period exists in DB
    period = db.query(AssessmentPeriod).filter(AssessmentPeriod.period_id == assessment_period_id).first()
    if not period:
        db.add(AssessmentPeriod(
            period_id=assessment_period_id,
            name=f"Assessment Period {assessment_period_id}",
            start_date=now_utc,
            end_date=now_utc,
            is_active=True,
            created_at=now_utc
        ))
        db.flush()

    # RUN ISOLATION: Mark all previous runs for this period as is_latest = False
    db.query(AnalysisRun).filter(
        AnalysisRun.assessment_period_id == assessment_period_id,
        AnalysisRun.is_latest.is_(True)
    ).update({"is_latest": False})
    db.flush()

    query = db.query(Entity)
    if entity_ids:
        query = query.filter(Entity.entity_id.in_(entity_ids))
    entities = query.all()

    total_alerts_analyzed = 0
    total_cases_analyzed = 0
    all_created_findings: List[Finding] = []
    all_evidence_links: List[FindingEvidenceLink] = []
    all_capability_scores: List[CapabilityScore] = []

    # 1. Peer Benchmarking across cohort
    peer_data = evaluate_peer_benchmarking(db, assessment_period_id=assessment_period_id)

    # 2. Operational Anomaly Detection with First-Class Findings (Section 12)
    anomaly_summary, anomaly_findings_with_links = detect_operational_anomalies(
        db,
        assessment_period_id=assessment_period_id,
        run_id=run_id
    )
    for anom_finding, anom_links in anomaly_findings_with_links:
        all_created_findings.append(anom_finding)
        all_evidence_links.extend(anom_links)

    entity_risk_summaries: Dict[str, Any] = {}

    for ent in entities:
        eid = ent.entity_id
        ent_alerts = db.query(Alert).filter(
            Alert.entity_id == eid,
            Alert.assessment_period_id == assessment_period_id
        ).all()
        if not ent_alerts:
            ent_alerts = db.query(Alert).filter(Alert.entity_id == eid).all()

        ent_cases = db.query(Case).filter(
            Case.entity_id == eid,
            Case.assessment_period_id == assessment_period_id
        ).all()
        if not ent_cases:
            ent_cases = db.query(Case).filter(Case.entity_id == eid).all()

        total_alerts_analyzed += len(ent_alerts)
        total_cases_analyzed += len(ent_cases)

        # 3. Execution Gaps (Rules A - H)
        gap_results = evaluate_execution_gaps_for_entity(db, run_id, eid, assessment_period_id=assessment_period_id)

        # 4. Negative Space Expectation Engine
        neg_results = evaluate_negative_space_for_entity(db, run_id, eid, assessment_period_id=assessment_period_id)

        ent_findings = []
        for finding, links in (gap_results + neg_results):
            all_created_findings.append(finding)
            all_evidence_links.extend(links)
            ent_findings.append(finding)

        # Also count anomalies for this entity
        anom_findings_for_ent = [f for f, _ in anomaly_findings_with_links if f.entity_id == eid]
        ent_findings.extend(anom_findings_for_ent)

        # 5. 8 Capability Dimensions (Evidence-backed)
        cap_scores = evaluate_8_capability_dimensions(db, run_id, eid, assessment_period_id=assessment_period_id)
        all_capability_scores.extend(cap_scores)

        peer_dev_count = len(peer_data.get("entity_benchmarks", {}).get(eid, {}).get("deviations", []))
        anomaly_count = len(anomaly_summary.get("anomalies_by_entity", {}).get(eid, []))

        # 6. Supervisory Attention Indicator
        level, score, breakdown = calculate_supervisory_attention_indicator(
            findings=ent_findings,
            capability_scores=cap_scores,
            peer_deviations=peer_dev_count,
            anomalies_count=anomaly_count
        )

        entity_risk_summaries[eid] = {
            "entity_name": ent.name,
            "sector": ent.sector,
            "claimed_tier": ent.claimed_tier,
            "supervisory_attention_level": level,
            "supervisory_attention_score": score,
            "score_breakdown": breakdown,
            "findings_count": len(ent_findings),
            "execution_gaps": sum(1 for f in ent_findings if f.category == "EXECUTION_GAP"),
            "negative_space": sum(1 for f in ent_findings if f.category == "NEGATIVE_SPACE"),
            "anomalies_count": sum(1 for f in ent_findings if f.category == "ANOMALY"),
            "peer_deviations": peer_dev_count
        }

    # Persist findings, evidence links, and capability scores
    for f in all_created_findings:
        db.add(f)
    db.flush()

    for link in all_evidence_links:
        db.add(link)

    for cs in all_capability_scores:
        db.add(cs)

    # Sync Review Queue Idempotently (Section 19)
    # Preserves supervisor state (CONFIRMED, REJECTED, DEFERRED, notes, reviewer) across reruns!
    for finding in all_created_findings:
        if finding.severity in ["CRITICAL", "HIGH"]:
            existing_rev = db.query(ReviewItem).filter(
                ReviewItem.entity_id == finding.entity_id,
                ReviewItem.finding_id == finding.finding_id
            ).first()

            if not existing_rev:
                # Check if identical finding type existed in previous run for same entity
                prev_rev = db.query(ReviewItem).filter(
                    ReviewItem.entity_id == finding.entity_id,
                    ReviewItem.assessment_period_id == assessment_period_id
                ).first()

                preserved_status = prev_rev.status if (prev_rev and prev_rev.status in ["CONFIRMED", "REJECTED", "DEFERRED", "UNDER_REVIEW", "REQUEST_EVIDENCE"]) else "OPEN"
                preserved_reviewer = prev_rev.assigned_reviewer if prev_rev else None
                preserved_notes = prev_rev.notes if prev_rev else None

                rev_item = ReviewItem(
                    review_id=f"REV-{uuid.uuid4().hex[:8].upper()}",
                    finding_id=finding.finding_id,
                    entity_id=finding.entity_id,
                    assessment_period_id=assessment_period_id,
                    run_id=run_id,
                    priority=finding.severity,
                    status=preserved_status,
                    assigned_reviewer=preserved_reviewer,
                    notes=preserved_notes
                )
                db.add(rev_item)

    execution_duration = round(time.time() - start_time, 2)
    completed_utc = utc_now()

    summary_payload = {
        "note": note,
        "assessment_period_id": assessment_period_id,
        "config_hash": config_hash,
        "entity_attention_summary": entity_risk_summaries,
        "critical_findings": sum(1 for f in all_created_findings if f.severity == "CRITICAL"),
        "high_findings": sum(1 for f in all_created_findings if f.severity == "HIGH"),
        "execution_gaps_total": sum(1 for f in all_created_findings if f.category == "EXECUTION_GAP"),
        "negative_space_total": sum(1 for f in all_created_findings if f.category == "NEGATIVE_SPACE"),
        "anomalies_total": sum(1 for f in all_created_findings if f.category == "ANOMALY")
    }

    analysis_run = AnalysisRun(
        run_id=run_id,
        assessment_period_id=assessment_period_id,
        timestamp=now_utc,
        started_at=now_utc,
        completed_at=completed_utc,
        dataset_version=dataset_version,
        ruleset_version=RULESET_VERSION,
        analytics_version=ANALYTICS_VERSION,
        model_version=MODEL_VERSION,
        config_hash=config_hash,
        is_latest=True,
        status="COMPLETED",
        entities_analyzed_count=len(entities),
        alerts_analyzed_count=total_alerts_analyzed,
        cases_analyzed_count=total_cases_analyzed,
        findings_count=len(all_created_findings),
        summary_json=json.dumps(summary_payload),
        execution_time_seconds=execution_duration
    )
    db.add(analysis_run)

    # Append cryptographic audit event with SHA-256 hash chaining (Section 20)
    append_audit_event(
        db=db,
        action="ANALYSIS_RUN",
        actor="SUPERVISOR",
        entity_id=None,
        details={
            "run_id": run_id,
            "assessment_period_id": assessment_period_id,
            "entities_analyzed": len(entities),
            "findings_count": len(all_created_findings),
            "config_hash": config_hash,
            "is_latest": True,
            "execution_time_seconds": execution_duration
        }
    )

    db.commit()
    db.refresh(analysis_run)

    return analysis_run
