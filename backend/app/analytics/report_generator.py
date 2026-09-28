import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import APP_NAME, APP_VERSION, RULESET_VERSION, ANALYTICS_VERSION, MODEL_VERSION
from app.models.analysis_run import AnalysisRun, CapabilityScore
from app.models.entity import Entity, AssessmentPeriod, DatasetProvenance
from app.models.finding import Finding
from app.models.audit import AuditLog, ReviewItem
from app.analytics.peer_benchmarking import evaluate_peer_benchmarking
from app.analytics.anomaly_engine import detect_operational_anomalies
from app.analytics.temporal_drift import evaluate_temporal_drift
from app.analytics.sample_prioritizer import prioritize_alert_review_samples
from app.analytics.validation_harness import run_synthetic_ground_truth_benchmark, evaluate_expert_review_mode
from app.analytics.data_quality import evaluate_dataset_quality
from app.analytics.engine import get_authoritative_entity_metrics
from app.time_utils import utc_now


def generate_supervisory_report(
    db: Session,
    run_id: Optional[str] = None,
    assessment_period_id: str = "2026-Q2"
) -> Dict[str, Any]:
    """
    Generates a formal supervisory assessment report with prominent synthetic data disclaimer (Sections 30 & 31).
    All statistical signals are classified accurately as POTENTIAL FINDINGS / SUPERVISORY SIGNALS requiring human review.
    """
    # 1. Fetch Run
    if run_id:
        run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    else:
        run = db.query(AnalysisRun).filter(
            AnalysisRun.assessment_period_id == assessment_period_id,
            AnalysisRun.is_latest.is_(True),
            AnalysisRun.status == "COMPLETED"
        ).first()
        if not run:
            run = db.query(AnalysisRun).filter(AnalysisRun.status == "COMPLETED").order_by(AnalysisRun.timestamp.desc()).first()

    if not run:
        return {"error": "No completed assessment runs found in database."}

    active_run_id = run.run_id
    period_id = run.assessment_period_id or assessment_period_id

    # 2. Scope & Entities
    entities = db.query(Entity).all()
    findings = db.query(Finding).filter(Finding.run_id == active_run_id).all()
    capability_scores = db.query(CapabilityScore).filter(CapabilityScore.run_id == active_run_id).all()
    provenances = db.query(DatasetProvenance).filter(DatasetProvenance.assessment_period_id == period_id).all()
    review_items = db.query(ReviewItem).filter(ReviewItem.assessment_period_id == period_id).all()

    # Analytical sub-modules
    data_quality = evaluate_dataset_quality(db, assessment_period_id=period_id)
    peers = evaluate_peer_benchmarking(db, assessment_period_id=period_id)
    anomalies_summary, _ = detect_operational_anomalies(db, assessment_period_id=period_id, run_id=active_run_id)
    trends = evaluate_temporal_drift(db)
    samples = prioritize_alert_review_samples(db, assessment_period_id=period_id, limit=20)
    validation_mode_a = run_synthetic_ground_truth_benchmark(db, run_id=active_run_id)
    validation_mode_b = evaluate_expert_review_mode(db, run_id=active_run_id)

    # Authoritative entity metrics
    entity_evaluations = [
        get_authoritative_entity_metrics(db, ent.entity_id, run_id=active_run_id, assessment_period_id=period_id)
        for ent in entities
    ]

    attention_entities = [
        e for e in entity_evaluations
        if e.get("supervisory_attention_level") in ["CRITICAL", "HIGH"]
    ]

    last_audit = db.query(AuditLog).order_by(AuditLog.id.desc()).first()

    report_data = {
        "report_metadata": {
            "title": "SUPERVISORY SOC OPERATIONAL ASSESSMENT REPORT",
            # Prominent classification banner (Section 31)
            "classification": "DEMO / SYNTHETIC DATA — NOT FOR OPERATIONAL USE",
            "classification_banner": "DEMO / SYNTHETIC DATA — NOT FOR OPERATIONAL USE",
            "mode": "AIR_GAPPED_OFFLINE_LOCAL",
            "app_name": APP_NAME,
            "system_version": APP_VERSION,
            "ruleset_version": RULESET_VERSION,
            "analytics_version": ANALYTICS_VERSION,
            "model_version": MODEL_VERSION,
            "run_id": active_run_id,
            "assessment_period": period_id,
            "generated_timestamp": utc_now().isoformat(),
            "disclaimer": (
                "DEMO / SYNTHETIC DATA — NOT FOR OPERATIONAL USE. "
                "This report was generated in a local air-gapped prototype environment. "
                "All statistical deviations represent potential supervisory signals requiring human confirmation. "
                "Not real government data."
            )
        },
        "sections": {
            "1_executive_summary": {
                "total_entities_evaluated": len(entities),
                "entities_requiring_attention": len(attention_entities),
                "total_findings": len(findings),
                "critical_findings_count": sum(1 for f in findings if f.severity == "CRITICAL"),
                "high_findings_count": sum(1 for f in findings if f.severity == "HIGH"),
                "core_supervisory_verdict": (
                    f"{len(attention_entities)} out of {len(entities)} Critical Sector Entities exhibit notable execution gaps, "
                    f"telemetry negative space, or operational anomalies requiring supervisory inquiry."
                )
            },
            "2_scope_and_entities": {
                "entities": [
                    {
                        "entity_id": ent.entity_id,
                        "name": ent.name,
                        "sector": ent.sector,
                        "claimed_tier": ent.claimed_tier,
                        "monitored_asset_count": ent.monitored_asset_count,
                        "soc_model": ent.soc_model
                    }
                    for ent in entities
                ]
            },
            "3_dataset_and_provenance": {
                "provenance_records": [
                    {
                        "filename": p.filename,
                        "file_hash_sha256": p.file_hash,
                        "source_name": p.source_name,
                        "record_count": p.record_count,
                        "data_quality_pct": p.data_quality_pct,
                        "import_timestamp": p.import_timestamp.isoformat() if p.import_timestamp else None
                    }
                    for p in provenances
                ]
            },
            "4_data_quality_evaluation": data_quality,
            "5_entities_requiring_attention": attention_entities,
            "6_eight_dimension_capability_assessment": [
                {
                    "entity_id": cs.entity_id,
                    "dimension": cs.dimension,
                    "score": cs.score,
                    "status": cs.status,
                    "peer_median": cs.peer_median,
                    "deviation": cs.deviation,
                    "confidence": cs.confidence,
                    "trend": cs.trend
                }
                for cs in capability_scores
            ],
            "7_execution_gaps": [
                {
                    "finding_id": f.finding_id,
                    "entity_id": f.entity_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "rule_id": f.rule_id,
                    "reason": f.reason,
                    "evidence_summary": f.evidence_summary,
                    "recommended_review_area": f.recommended_review_area,
                    "sample_size": f.sample_size,
                    "evidence_records_count": len(f.evidence_links)
                }
                for f in findings if f.category == "EXECUTION_GAP"
            ],
            "8_negative_space": [
                {
                    "finding_id": f.finding_id,
                    "entity_id": f.entity_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "rule_id": f.rule_id,
                    "reason": f.reason,
                    "evidence_summary": f.evidence_summary,
                    "recommended_review_area": f.recommended_review_area,
                    "evidence_records_count": len(f.evidence_links)
                }
                for f in findings if f.category == "NEGATIVE_SPACE"
            ],
            "9_operational_anomalies": [
                {
                    "finding_id": f.finding_id,
                    "entity_id": f.entity_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "rule_id": f.rule_id,
                    "reason": f.reason,
                    "evidence_summary": f.evidence_summary,
                    "recommended_review_area": f.recommended_review_area
                }
                for f in findings if f.category == "ANOMALY"
            ],
            "10_peer_benchmarking": peers,
            "11_temporal_trends_and_drift": trends,
            "12_prioritized_review_samples": samples,
            "13_review_queue_and_actions": [
                {
                    "review_id": r.review_id,
                    "finding_id": r.finding_id,
                    "entity_id": r.entity_id,
                    "status": r.status,
                    "priority": r.priority,
                    "assigned_reviewer": r.assigned_reviewer,
                    "notes": r.notes,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None
                }
                for r in review_items
            ],
            "14_validation_framework": {
                "synthetic_ground_truth_benchmark": validation_mode_a,
                "human_expert_review_mode": validation_mode_b
            },
            "15_supervisory_methodology": {
                "framework": "Offline-First Deterministic + Statistical Baseline Supervisory Assessment",
                "ruleset_version": RULESET_VERSION,
                "capability_model": "8 Official SIH26157 Supervisory Dimensions",
                "negative_space_approach": "Expectation model contrasting declared scope against observed telemetry",
                "anomaly_engine": "Adaptive Isolation Forest + Robust MAD modified z-scores",
                "principles": [
                    "Explainable, deterministic calculations with verifiable metrics",
                    "Direct evidence drill-down from finding to raw source records",
                    "Supervisor remains authoritative final decision-maker"
                ]
            },
            "16_limitations": [
                "Assessment is strictly based on periodic batch submissions rather than real-time wire taps",
                "Statistical outliers represent potential deviations requiring human inspection, not proven infractions",
                "Sensor blind spots cannot be independently verified without physical network tap validation"
            ],
            "17_tamper_evident_audit_information": {
                "latest_event_hash": last_audit.event_hash if last_audit else None,
                "previous_event_hash": last_audit.previous_event_hash if last_audit else None,
                "total_audited_events": db.query(AuditLog).count()
            },
            "18_analysis_run_information": {
                "run_id": run.run_id,
                "assessment_period_id": run.assessment_period_id,
                "timestamp": run.timestamp.isoformat() if run.timestamp else None,
                "execution_time_seconds": run.execution_time_seconds,
                "config_hash": run.config_hash,
                "alerts_analyzed": run.alerts_analyzed_count,
                "cases_analyzed": run.cases_analyzed_count
            }
        }
    }

    return report_data


def generate_markdown_supervisory_report(report_data: Dict[str, Any]) -> str:
    """
    Renders report_data as a clean, professional Markdown supervisory audit report (Section 30).
    Includes prominent classification and disclaimers (Section 31).
    """
    meta = report_data.get("report_metadata", {})
    sec = report_data.get("sections", {})

    lines = [
        f"# {meta.get('title', 'SUPERVISORY SOC OPERATIONAL ASSESSMENT REPORT')}",
        "",
        f"> **CLASSIFICATION**: {meta.get('classification', 'DEMO / SYNTHETIC DATA — NOT FOR OPERATIONAL USE')}",
        f"> **ASSESSMENT PERIOD**: `{meta.get('assessment_period', '2026-Q2')}` | **RUN ID**: `{meta.get('run_id', 'N/A')}`",
        f"> **GENERATED AT**: {meta.get('generated_timestamp', '')}",
        f"> **DISCLAIMER**: {meta.get('disclaimer', '')}",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Entities Evaluated**: {sec.get('1_executive_summary', {}).get('total_entities_evaluated', 0)}",
        f"- **Entities Requiring Supervisory Attention**: {sec.get('1_executive_summary', {}).get('entities_requiring_attention', 0)}",
        f"- **Total Supervisory Findings**: {sec.get('1_executive_summary', {}).get('total_findings', 0)} (Critical: {sec.get('1_executive_summary', {}).get('critical_findings_count', 0)}, High: {sec.get('1_executive_summary', {}).get('high_findings_count', 0)})",
        f"- **Verdict**: {sec.get('1_executive_summary', {}).get('core_supervisory_verdict', '')}",
        "",
        "## 2. Data Quality Summary",
        "",
        f"- **Completeness**: {sec.get('4_data_quality_evaluation', {}).get('completeness_pct', 0)}%",
        f"- **Validity**: {sec.get('4_data_quality_evaluation', {}).get('validity_pct', 0)}%",
        f"- **Timestamp Quality**: {sec.get('4_data_quality_evaluation', {}).get('timestamp_quality_pct', 0)}%",
        f"- **Evidence Coverage**: {sec.get('4_data_quality_evaluation', {}).get('evidence_coverage_pct', 0)}%",
        f"- **Analytical Confidence**: {int(sec.get('4_data_quality_evaluation', {}).get('confidence_factor', 1.0) * 100)}%",
        "",
        "## 3. Entities Requiring Supervisory Attention",
        "",
        "| Entity ID | Name | Sector | Attention Level | Attention Score | Gaps | Negative Space |",
        "|-----------|------|--------|-----------------|-----------------|------|----------------|"
    ]

    for ent in sec.get("5_entities_requiring_attention", []):
        lines.append(
            f"| `{ent.get('entity_id')}` | {ent.get('name')} | {ent.get('sector')} | **{ent.get('supervisory_attention_level', ent.get('attention_level'))}** | {ent.get('supervisory_attention_score', ent.get('attention_score'))} | {ent.get('execution_gaps_count', ent.get('gaps_count'))} | {ent.get('negative_space_count')} |"
        )

    lines.extend([
        "",
        "## 4. Execution Gaps",
        ""
    ])

    for gap in sec.get("7_execution_gaps", []):
        lines.append(f"### Finding `{gap.get('finding_id')}`: {gap.get('finding_type')}")
        lines.append(f"- **Entity**: `{gap.get('entity_id')}` | **Severity**: `{gap.get('severity')}` | **Confidence**: {gap.get('confidence')}")
        lines.append(f"- **Reason**: {gap.get('reason')}")
        lines.append(f"- **Recommended Review**: {gap.get('recommended_review_area')}")
        lines.append("")

    lines.extend([
        "## 5. Negative Space & Coverage Gaps",
        ""
    ])

    for neg in sec.get("8_negative_space", []):
        lines.append(f"### Finding `{neg.get('finding_id')}`: {neg.get('finding_type')}")
        lines.append(f"- **Entity**: `{neg.get('entity_id')}` | **Severity**: `{neg.get('severity')}`")
        lines.append(f"- **Reason**: {neg.get('reason')}")
        lines.append(f"- **Recommended Review**: {neg.get('recommended_review_area')}")
        lines.append("")

    lines.extend([
        "## 6. Tamper-Evident Audit Verification",
        "",
        f"- **Latest Event Hash (SHA-256)**: `{sec.get('17_tamper_evident_audit_information', {}).get('latest_event_hash')}`",
        f"- **Previous Event Hash**: `{sec.get('17_tamper_evident_audit_information', {}).get('previous_event_hash')}`",
        f"- **Total Cryptographically Audited Events**: {sec.get('17_tamper_evident_audit_information', {}).get('total_audited_events')}",
        "",
        "---",
        "*Report end — Generated by SAT-SA Supervisory Analytics Platform*"
    ])

    return "\n".join(lines)


# Alias for backward compatibility
export_report_to_markdown = generate_markdown_supervisory_report
