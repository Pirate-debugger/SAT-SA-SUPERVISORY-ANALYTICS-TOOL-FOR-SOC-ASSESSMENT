import time
import json
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import RULESET_VERSION, ANALYTICS_VERSION
from app.models.entity import Entity, Asset, AssessmentPeriod
from app.models.alert import Alert
from app.models.case import Case
from app.models.analysis_run import AnalysisRun, CapabilityScore
from app.models.finding import Finding, FindingEvidenceLink
from app.models.audit import AuditLog, ReviewItem
from app.analytics.execution_gaps import evaluate_execution_gaps_for_entity
from app.analytics.negative_space import evaluate_negative_space_for_entity
from app.analytics.capability_dimensions import evaluate_8_capability_dimensions
from app.analytics.peer_benchmarking import evaluate_peer_benchmarking
from app.analytics.anomaly_engine import detect_operational_anomalies
from app.ingestion.pipeline import append_audit_event


def calculate_supervisory_attention_indicator(
    findings: List[Finding],
    capability_scores: List[CapabilityScore],
    peer_deviations: int = 0,
    anomalies_count: int = 0
) -> Tuple[str, float, Dict[str, float]]:
    """
    Computes explainable Supervisory Attention Indicator (SAI).
    Returns (level: CRITICAL/HIGH/MODERATE/LOW, score: 0-100, component_contributions)
    """
    gap_score = sum(30.0 if f.severity == "CRITICAL" else (18.0 if f.severity == "HIGH" else 8.0)
                    for f in findings if f.category == "EXECUTION_GAP")

    neg_score = sum(25.0 if f.severity == "CRITICAL" else 15.0
                    for f in findings if f.category == "NEGATIVE_SPACE")

    # Capability score deficit (average below 75)
    cap_deficit = 0.0
    if capability_scores:
        avg_cap = sum(c.score for c in capability_scores) / len(capability_scores)
        if avg_cap < 75.0:
            cap_deficit = (75.0 - avg_cap) * 0.8

    peer_penalty = min(20.0, peer_deviations * 8.0)
    anomaly_penalty = min(15.0, anomalies_count * 5.0)

    total_score = gap_score + neg_score + cap_deficit + peer_penalty + anomaly_penalty
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
        "execution_gaps_contribution": round(gap_score, 1),
        "negative_space_contribution": round(neg_score, 1),
        "capability_deficit_contribution": round(cap_deficit, 1),
        "peer_deviations_contribution": round(peer_penalty, 1),
        "anomaly_contribution": round(anomaly_penalty, 1)
    }

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


def execute_supervisory_analysis_run(
    db: Session,
    entity_ids: Optional[List[str]] = None,
    assessment_period_id: str = "2026-Q2",
    dataset_version: str = "v1.0-offline",
    note: str = "Periodic Supervisory Assessment"
) -> AnalysisRun:
    start_time = time.time()
    run_id = f"RUN-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    # Compute config hash for idempotency checking
    config_str = f"{assessment_period_id}:{sorted(entity_ids or [])}:{dataset_version}:{RULESET_VERSION}"
    config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]

    # Ensure assessment period exists in DB
    period = db.query(AssessmentPeriod).filter(AssessmentPeriod.period_id == assessment_period_id).first()
    if not period:
        db.add(AssessmentPeriod(
            period_id=assessment_period_id,
            name=f"Assessment Period {assessment_period_id}",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 6, 30),
            is_active=True
        ))
        db.flush()

    # IDEMPOTENCY FIX: Mark all previous runs for this assessment period as is_latest = False
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

    # Run peer benchmarking & anomaly detection across the peer pool
    peer_data = evaluate_peer_benchmarking(db, assessment_period_id=assessment_period_id)
    anomaly_data = detect_operational_anomalies(db, assessment_period_id=assessment_period_id)

    entity_risk_summaries: Dict[str, Any] = {}

    for ent in entities:
        eid = ent.entity_id
        ent_alerts_count = db.query(Alert).filter(
            Alert.entity_id == eid,
            Alert.assessment_period_id == assessment_period_id
        ).count()
        if ent_alerts_count == 0:
            ent_alerts_count = db.query(Alert).filter(Alert.entity_id == eid).count()

        ent_cases_count = db.query(Case).filter(
            Case.entity_id == eid,
            Case.assessment_period_id == assessment_period_id
        ).count()
        if ent_cases_count == 0:
            ent_cases_count = db.query(Case).filter(Case.entity_id == eid).count()

        total_alerts_analyzed += ent_alerts_count
        total_cases_analyzed += ent_cases_count

        # 1. Execution Gaps
        gap_results = evaluate_execution_gaps_for_entity(db, run_id, eid, assessment_period_id=assessment_period_id)

        # 2. Negative Space
        neg_results = evaluate_negative_space_for_entity(db, run_id, eid, assessment_period_id=assessment_period_id)

        ent_findings = []
        for finding, links in (gap_results + neg_results):
            all_created_findings.append(finding)
            all_evidence_links.extend(links)
            ent_findings.append(finding)

        # 3. 8 Capability Dimensions
        cap_scores = evaluate_8_capability_dimensions(db, run_id, eid, assessment_period_id=assessment_period_id)
        all_capability_scores.extend(cap_scores)

        # Peer and anomaly inputs
        peer_dev_count = len(peer_data.get("entity_benchmarks", {}).get(eid, {}).get("deviations", []))
        anomaly_count = len(anomaly_data.get("anomalies_by_entity", {}).get(eid, []))

        # 4. Supervisory Attention Indicator
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
            "peer_deviations": peer_dev_count,
            "anomalies_count": anomaly_count
        }

    # Persist findings and capability scores
    for f in all_created_findings:
        db.add(f)
    db.flush()

    for link in all_evidence_links:
        db.add(link)

    for cs in all_capability_scores:
        db.add(cs)

    # Sync Review Queue Idempotently (preventing duplicated items or wiping supervisor decisions)
    for finding in all_created_findings:
        if finding.severity in ["CRITICAL", "HIGH"]:
            # Check existing review item
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

                # If previously reviewed/confirmed/rejected, preserve supervisor state!
                preserved_status = prev_rev.status if (prev_rev and prev_rev.status in ["CONFIRMED", "REJECTED", "DEFERRED", "UNDER_REVIEW"]) else "OPEN"
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

    summary_payload = {
        "note": note,
        "assessment_period_id": assessment_period_id,
        "config_hash": config_hash,
        "entity_attention_summary": entity_risk_summaries,
        "critical_findings": sum(1 for f in all_created_findings if f.severity == "CRITICAL"),
        "high_findings": sum(1 for f in all_created_findings if f.severity == "HIGH"),
        "execution_gaps_total": sum(1 for f in all_created_findings if f.category == "EXECUTION_GAP"),
        "negative_space_total": sum(1 for f in all_created_findings if f.category == "NEGATIVE_SPACE")
    }

    analysis_run = AnalysisRun(
        run_id=run_id,
        assessment_period_id=assessment_period_id,
        timestamp=datetime.utcnow(),
        dataset_version=dataset_version,
        ruleset_version=RULESET_VERSION,
        analytics_version=ANALYTICS_VERSION,
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

    # Append cryptographic audit event with SHA-256 hash chaining
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
