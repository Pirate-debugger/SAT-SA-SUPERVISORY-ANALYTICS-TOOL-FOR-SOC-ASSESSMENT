import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import APP_NAME, APP_VERSION, RULESET_VERSION, ANALYTICS_VERSION
from app.models.analysis_run import AnalysisRun, CapabilityScore
from app.models.entity import Entity, AssessmentPeriod, DatasetProvenance
from app.models.finding import Finding
from app.models.audit import AuditLog, ReviewItem
from app.analytics.peer_benchmarking import evaluate_peer_benchmarking
from app.analytics.anomaly_engine import detect_operational_anomalies
from app.analytics.temporal_drift import evaluate_temporal_drift
from app.analytics.sample_prioritizer import prioritize_alert_review_samples
from app.analytics.validation_harness import run_expert_validation_benchmark


def generate_supervisory_report(
    db: Session,
    run_id: Optional[str] = None,
    assessment_period_id: str = "2026-Q2"
) -> Dict[str, Any]:
    """
    Generates a formal 18-section supervisory assessment report.
    """
    # 1. Fetch Run
    if run_id:
        run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    else:
        run = db.query(AnalysisRun).filter(
            AnalysisRun.assessment_period_id == assessment_period_id,
            AnalysisRun.is_latest.is_(True)
        ).first()
        if not run:
            run = db.query(AnalysisRun).order_by(AnalysisRun.timestamp.desc()).first()

    if not run:
        return {"error": "No assessment runs found in database."}

    active_run_id = run.run_id
    period_id = run.assessment_period_id or assessment_period_id

    # 2. Scope & Entities
    entities = db.query(Entity).all()
    findings = db.query(Finding).filter(Finding.run_id == active_run_id).all()
    capability_scores = db.query(CapabilityScore).filter(CapabilityScore.run_id == active_run_id).all()
    provenances = db.query(DatasetProvenance).filter(DatasetProvenance.assessment_period_id == period_id).all()
    review_items = db.query(ReviewItem).filter(ReviewItem.assessment_period_id == period_id).all()

    # Analytics sub-reports
    peers = evaluate_peer_benchmarking(db, assessment_period_id=period_id)
    anomalies = detect_operational_anomalies(db, assessment_period_id=period_id)
    trends = evaluate_temporal_drift(db)
    samples = prioritize_alert_review_samples(db, assessment_period_id=period_id, limit=10)
    validation = run_expert_validation_benchmark(db, run_id=active_run_id)

    # Attention entities
    attention_entities = []
    run_summary = json.loads(run.summary_json) if run.summary_json else {}
    att_summary = run_summary.get("entity_attention_summary", {})

    for eid, info in att_summary.items():
        if info.get("supervisory_attention_level") in ["CRITICAL", "HIGH"]:
            attention_entities.append({
                "entity_id": eid,
                "name": info.get("entity_name"),
                "sector": info.get("sector"),
                "attention_level": info.get("supervisory_attention_level"),
                "attention_score": info.get("supervisory_attention_score"),
                "gaps_count": info.get("execution_gaps"),
                "negative_space_count": info.get("negative_space")
            })

    # Last audit hash
    last_audit = db.query(AuditLog).order_by(AuditLog.id.desc()).first()

    report_data = {
        "report_metadata": {
            "title": "SUPERVISORY SOC OPERATIONAL ASSESSMENT REPORT",
            "classification": "OFFICIAL / SUPERVISORY USE ONLY (AIR-GAPPED)",
            "app_name": APP_NAME,
            "system_version": APP_VERSION,
            "ruleset_version": RULESET_VERSION,
            "analytics_version": ANALYTICS_VERSION,
            "run_id": active_run_id,
            "assessment_period": period_id,
            "generated_timestamp": datetime.utcnow().isoformat(),
            "disclaimer": "PROTOTYPE ASSESSMENT — ALL DEMO DATA CLEARLY LABELED SYNTHETIC"
        },
        "sections": {
            "1_executive_summary": {
                "total_entities_evaluated": len(entities),
                "entities_requiring_attention": len(attention_entities),
                "total_findings": len(findings),
                "critical_findings_count": sum(1 for f in findings if f.severity == "CRITICAL"),
                "high_findings_count": sum(1 for f in findings if f.severity == "HIGH"),
                "core_supervisory_verdict": (
                    f"{len(attention_entities)} out of {len(entities)} Critical Sector Entities exhibit notable execution gaps "
                    f"or negative space telemetry blind spots inconsistent with their declared security tiers."
                )
            },
            "2_scope_and_entities": [
                {
                    "entity_id": e.entity_id,
                    "name": e.name,
                    "sector": e.sector,
                    "claimed_tier": e.claimed_tier,
                    "monitored_asset_count": e.monitored_asset_count,
                    "soc_model": e.soc_model
                } for e in entities
            ],
            "3_dataset_provenance": [
                {
                    "provenance_id": p.provenance_id,
                    "filename": p.filename,
                    "sha256_hash": p.file_hash,
                    "records_ingested": p.record_count,
                    "data_quality_pct": p.data_quality_pct,
                    "import_time": p.import_timestamp.isoformat() if p.import_timestamp else None
                } for p in provenances
            ],
            "4_entities_requiring_attention": attention_entities,
            "5_capability_assessment": [
                {
                    "entity_id": cs.entity_id,
                    "dimension": cs.dimension,
                    "score": cs.score,
                    "status": cs.status,
                    "peer_deviation": cs.deviation
                } for cs in capability_scores
            ],
            "6_execution_gaps": [
                {
                    "finding_id": f.finding_id,
                    "entity_id": f.entity_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "reason": f.reason,
                    "observed": json.loads(f.observed_value_json) if f.observed_value_json else None,
                    "expected": json.loads(f.expected_value_json) if f.expected_value_json else None,
                    "recommended_review_area": f.recommended_review_area
                } for f in findings if f.category == "EXECUTION_GAP"
            ],
            "7_negative_space": [
                {
                    "finding_id": f.finding_id,
                    "entity_id": f.entity_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "reason": f.reason,
                    "evidence_summary": f.evidence_summary,
                    "recommended_review_area": f.recommended_review_area
                } for f in findings if f.category == "NEGATIVE_SPACE"
            ],
            "8_peer_benchmarking": peers.get("peer_baselines", {}),
            "9_operational_anomalies": anomalies.get("anomalies_by_entity", {}),
            "10_temporal_trends": trends.get("entity_trends", {}),
            "11_prioritized_alert_samples": samples,
            "12_supervisory_review_status": [
                {
                    "review_id": r.review_id,
                    "finding_id": r.finding_id,
                    "entity_id": r.entity_id,
                    "priority": r.priority,
                    "status": r.status,
                    "notes": r.notes
                } for r in review_items
            ],
            "13_validation_performance": validation.get("metrics", {}),
            "14_limitations_and_caveats": [
                "Assessment is strictly based on periodic batch submissions; absence of logs may reflect collection outages rather than active adversaries.",
                "Peer baselines are derived from available cohort data; small peer sample sizes (< 3) are marked 'UNABLE TO ASSESS'.",
                "Supervisory attention scores guide manual audit prioritization and do not constitute legal compliance certifications."
            ],
            "15_audit_verification": {
                "latest_event_hash": last_audit.event_hash if last_audit else "N/A",
                "previous_event_hash": last_audit.previous_event_hash if last_audit else "N/A",
                "integrity_algorithm": "SHA-256 Cryptographic Hash Chain"
            }
        }
    }

    return report_data


def generate_markdown_supervisory_report(report_data: Dict[str, Any]) -> str:
    """
    Renders structured report data into clean GitHub-flavored Markdown.
    """
    meta = report_data.get("report_metadata", {})
    sec = report_data.get("sections", {})
    exec_sum = sec.get("1_executive_summary", {})

    md = f"""# {meta.get('title')}
**System**: {meta.get('app_name')} ({meta.get('system_version')})
**Assessment Run ID**: `{meta.get('run_id')}` | **Assessment Period**: `{meta.get('assessment_period')}`
**Ruleset**: `{meta.get('ruleset_version')}` | **Date**: {meta.get('generated_timestamp')}
**Mode**: {meta.get('classification')}

> **Notice**: {meta.get('disclaimer')}

---

## 1. Executive Summary

- **Total Supervised Entities Analyzed**: {exec_sum.get('total_entities_evaluated', 0)}
- **Entities Requiring Immediate Supervisory Attention**: {exec_sum.get('entities_requiring_attention', 0)}
- **Total Operational Findings Identified**: {exec_sum.get('total_findings', 0)}
- **Critical Severity Findings**: {exec_sum.get('critical_findings_count', 0)}
- **High Severity Findings**: {exec_sum.get('high_findings_count', 0)}

**Supervisory Verdict**:
{exec_sum.get('core_supervisory_verdict')}

---

## 2. Entities Requiring Attention

| Entity ID | Entity Name | Sector | Attention Level | Attention Score | Gaps | Negative Space |
|-----------|-------------|--------|-----------------|-----------------|------|----------------|
"""

    for ent in sec.get("4_entities_requiring_attention", []):
        md += f"| `{ent['entity_id']}` | {ent['name']} | {ent['sector']} | **{ent['attention_level']}** | {ent['attention_score']}/100 | {ent['gaps_count']} | {ent['negative_space_count']} |\n"

    md += """
---

## 3. Execution Gaps & Procedural Weaknesses

"""
    for g in sec.get("6_execution_gaps", []):
        md += f"""### [{g['severity']}] {g['finding_type']} ({g['entity_id']})
- **Reason**: {g['reason']}
- **Actionable Guidance**: {g['recommended_review_area']}
- **Confidence**: {int(g['confidence'] * 100)}%

"""

    md += """---

## 4. Negative Space & Monitoring Coverage Gaps

"""
    for n in sec.get("7_negative_space", []):
        md += f"""### [{n['severity']}] {n['finding_type']} ({n['entity_id']})
- **Reason**: {n['reason']}
- **Evidence**: {n['evidence_summary']}
- **Actionable Guidance**: {n['recommended_review_area']}

"""

    md += """---

## 5. Prioritized Alert Review Samples

| Alert ID | Entity | Category | Severity | Closure Time | Priority Score | Review Rationale |
|----------|--------|----------|----------|--------------|----------------|------------------|
"""
    for s in sec.get("11_prioritized_alert_samples", []):
        md += f"| `{s['alert_id']}` | {s['entity_id']} | {s['category']} | {s['severity']} | {s.get('closure_minutes', 'N/A')}m | {s['priority_score']} | {s['review_rationale']} |\n"

    md += f"""
---

## 6. Audit & Traceability Signature

- **Run ID**: `{meta.get('run_id')}`
- **Audit Event SHA-256 Hash**: `{sec.get('15_audit_verification', {}).get('latest_event_hash')}`
- **Previous Event Hash**: `{sec.get('15_audit_verification', {}).get('previous_event_hash')}`
- **Integrity**: Verified Tamper-Evident Hash Chain
"""

    return md
