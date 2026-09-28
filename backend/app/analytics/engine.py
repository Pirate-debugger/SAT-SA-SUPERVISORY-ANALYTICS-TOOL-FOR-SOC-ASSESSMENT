import time
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import RULESET_VERSION, ANALYTICS_VERSION
from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.models.case import Case
from app.models.analysis_run import AnalysisRun
from app.models.finding import Finding, FindingEvidenceLink
from app.models.audit import AuditLog, ReviewItem
from app.analytics.execution_gaps import evaluate_execution_gaps_for_entity
from app.analytics.negative_space import evaluate_negative_space_for_entity


def calculate_entity_supervisory_risk(findings: List[Finding]) -> Tuple[str, float]:
    """
    Computes explainable supervisory risk from weighted evidence findings.
    Returns (risk_level: CRITICAL/HIGH/MODERATE/LOW, score: 0-100)
    """
    score = 0.0
    for f in findings:
        weight = 0.0
        if f.severity == "CRITICAL":
            weight = 30.0
        elif f.severity == "HIGH":
            weight = 18.0
        elif f.severity == "MEDIUM":
            weight = 8.0
        else:
            weight = 3.0

        # Adjust for confidence
        score += weight * (f.confidence or 0.8)

    # Cap score at 100.0
    score = min(100.0, round(score, 1))

    if score >= 60.0:
        level = "CRITICAL"
    elif score >= 40.0:
        level = "HIGH"
    elif score >= 20.0:
        level = "MODERATE"
    else:
        level = "LOW"

    return level, score


def execute_supervisory_analysis_run(
    db: Session,
    entity_ids: Optional[List[str]] = None,
    dataset_version: str = "v1.0-offline",
    note: str = "Periodic Supervisory Assessment"
) -> AnalysisRun:
    start_time = time.time()
    run_id = f"RUN-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    query = db.query(Entity)
    if entity_ids:
        query = query.filter(Entity.entity_id.in_(entity_ids))
    entities = query.all()

    total_alerts_analyzed = 0
    total_cases_analyzed = 0
    all_created_findings: List[Finding] = []
    all_evidence_links: List[FindingEvidenceLink] = []
    all_review_items: List[ReviewItem] = []

    entity_risk_summaries: Dict[str, Any] = {}

    for ent in entities:
        eid = ent.entity_id
        ent_alerts_count = db.query(Alert).filter(Alert.entity_id == eid).count()
        ent_cases_count = db.query(Case).filter(Case.entity_id == eid).count()
        total_alerts_analyzed += ent_alerts_count
        total_cases_analyzed += ent_cases_count

        # 1. Execution Gaps
        gap_results = evaluate_execution_gaps_for_entity(db, run_id, eid)

        # 2. Negative Space
        neg_results = evaluate_negative_space_for_entity(db, run_id, eid)

        ent_findings = []
        for finding, links in (gap_results + neg_results):
            all_created_findings.append(finding)
            all_evidence_links.extend(links)
            ent_findings.append(finding)

            # Auto-populate Review Queue for High & Critical findings
            if finding.severity in ["CRITICAL", "HIGH"]:
                rev_item = ReviewItem(
                    review_id=f"REV-{uuid.uuid4().hex[:8].upper()}",
                    finding_id=finding.finding_id,
                    entity_id=eid,
                    priority=finding.severity,
                    status="OPEN",
                    notes=f"Auto-queued for supervisory review based on {finding.finding_type} finding."
                )
                all_review_items.append(rev_item)

        risk_level, risk_score = calculate_entity_supervisory_risk(ent_findings)
        entity_risk_summaries[eid] = {
            "entity_name": ent.name,
            "sector": ent.sector,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "findings_count": len(ent_findings),
            "execution_gaps": sum(1 for f in ent_findings if f.category == "EXECUTION_GAP"),
            "negative_space": sum(1 for f in ent_findings if f.category == "NEGATIVE_SPACE")
        }

    # Persist findings and links
    for f in all_created_findings:
        db.add(f)
    db.flush()

    for link in all_evidence_links:
        db.add(link)

    for item in all_review_items:
        db.add(item)

    execution_duration = round(time.time() - start_time, 2)

    summary_payload = {
        "note": note,
        "entity_risks": entity_risk_summaries,
        "critical_findings": sum(1 for f in all_created_findings if f.severity == "CRITICAL"),
        "high_findings": sum(1 for f in all_created_findings if f.severity == "HIGH"),
        "execution_gaps_total": sum(1 for f in all_created_findings if f.category == "EXECUTION_GAP"),
        "negative_space_total": sum(1 for f in all_created_findings if f.category == "NEGATIVE_SPACE")
    }

    analysis_run = AnalysisRun(
        run_id=run_id,
        timestamp=datetime.utcnow(),
        dataset_version=dataset_version,
        ruleset_version=RULESET_VERSION,
        analytics_version=ANALYTICS_VERSION,
        status="COMPLETED",
        entities_analyzed_count=len(entities),
        alerts_analyzed_count=total_alerts_analyzed,
        cases_analyzed_count=total_cases_analyzed,
        findings_count=len(all_created_findings),
        summary_json=json.dumps(summary_payload),
        execution_time_seconds=execution_duration
    )
    db.add(analysis_run)

    # Audit Log
    audit = AuditLog(
        action="ANALYSIS_RUN",
        actor="SUPERVISOR",
        details_json=json.dumps({
            "run_id": run_id,
            "entities_analyzed": len(entities),
            "findings_count": len(all_created_findings),
            "execution_time_seconds": execution_duration
        })
    )
    db.add(audit)

    db.commit()
    db.refresh(analysis_run)

    return analysis_run
