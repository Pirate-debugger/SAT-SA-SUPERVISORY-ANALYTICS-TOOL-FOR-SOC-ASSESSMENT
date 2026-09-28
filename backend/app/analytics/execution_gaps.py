import json
import uuid
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding, FindingEvidenceLink


def evaluate_execution_gaps_for_entity(
    db: Session,
    run_id: str,
    entity_id: str,
    assessment_period_id: str = "2026-Q2"
) -> List[Tuple[Finding, List[FindingEvidenceLink]]]:
    findings_with_evidence: List[Tuple[Finding, List[FindingEvidenceLink]]] = []

    # 1. Critical Alerts Closed Unusually Quickly (< 10 minutes)
    critical_alerts = db.query(Alert).filter(
        Alert.entity_id == entity_id,
        Alert.assessment_period_id == assessment_period_id,
        Alert.severity.in_(["CRITICAL", "HIGH"]),
        Alert.closed_timestamp.isnot(None),
        Alert.alert_timestamp.isnot(None)
    ).all()

    if not critical_alerts:
        critical_alerts = db.query(Alert).filter(
            Alert.entity_id == entity_id,
            Alert.severity.in_(["CRITICAL", "HIGH"]),
            Alert.closed_timestamp.isnot(None),
            Alert.alert_timestamp.isnot(None)
        ).all()

    rapid_critical_alerts = []
    for a in critical_alerts:
        diff_seconds = (a.closed_timestamp - a.alert_timestamp).total_seconds()
        if 0 < diff_seconds < 600:  # Under 10 minutes
            rapid_critical_alerts.append(a)

    if len(rapid_critical_alerts) >= 5 and len(critical_alerts) > 0:
        pct_rapid = (len(rapid_critical_alerts) / len(critical_alerts)) * 100
        avg_rapid_mins = sum((a.closed_timestamp - a.alert_timestamp).total_seconds() for a in rapid_critical_alerts) / len(rapid_critical_alerts) / 60.0

        fnd_id = f"FND-GAP-RAPID-{uuid.uuid4().hex[:8].upper()}"
        finding = Finding(
            finding_id=fnd_id,
            run_id=run_id,
            entity_id=entity_id,
            assessment_period_id=assessment_period_id,
            finding_type="CRITICAL_ALERT_RAPID_CLOSURE",
            capability_dimension="SECURITY_OPERATIONS",
            category="EXECUTION_GAP",
            severity="CRITICAL",
            confidence=0.95,
            reason=(
                f"{len(rapid_critical_alerts)} high/critical alerts ({pct_rapid:.1f}% of critical volume) "
                f"were closed unusually quickly with an average duration of only {avg_rapid_mins:.1f} minutes. "
                f"Standard supervisory baseline requires at least 45-60 minutes for high-severity investigation."
            ),
            evidence_summary=f"Sample of {min(len(rapid_critical_alerts), 10)} alerts verified closed within minutes without deep triage.",
            observed_value_json=json.dumps({"avg_closure_minutes": round(avg_rapid_mins, 1), "rapid_alert_count": len(rapid_critical_alerts)}),
            expected_value_json=json.dumps({"supervisory_baseline_minutes": 60.0, "maximum_tolerated_rapid_pct": "5.0%"}),
            metric_values_json=json.dumps({
                "rapid_alerts_count": len(rapid_critical_alerts),
                "total_critical_alerts": len(critical_alerts),
                "percentage_rapid": round(pct_rapid, 1),
                "average_closure_minutes": round(avg_rapid_mins, 1)
            }),
            baseline_json=json.dumps({
                "threshold_minutes": 10.0,
                "expected_supervisory_baseline_minutes": 60.0
            }),
            recommended_review_area="Conduct manual audit of Tier-1 shift handover logs and examine closure rationale timestamps.",
            sample_size=len(rapid_critical_alerts),
            status="NEW"
        )
        evidence_links = [
            FindingEvidenceLink(
                finding_id=fnd_id,
                entity_id=entity_id,
                record_type="ALERT",
                record_id=a.alert_id,
                relevance_note=f"Closed in {round((a.closed_timestamp - a.alert_timestamp).total_seconds() / 60, 1)}m with disposition '{a.disposition}'"
            )
            for a in rapid_critical_alerts[:20]
        ]
        findings_with_evidence.append((finding, evidence_links))

    # 2. Critical Alerts Without Escalation
    un_escalated_critical = [a for a in critical_alerts if a.severity == "CRITICAL" and (a.escalated is False or a.escalated is None)]
    if len(un_escalated_critical) >= 3:
        fnd_id = f"FND-GAP-NOESC-{uuid.uuid4().hex[:8].upper()}"
        finding = Finding(
            finding_id=fnd_id,
            run_id=run_id,
            entity_id=entity_id,
            assessment_period_id=assessment_period_id,
            finding_type="CRITICAL_ALERTS_WITHOUT_ESCALATION",
            capability_dimension="ESCALATION",
            category="EXECUTION_GAP",
            severity="HIGH",
            confidence=0.92,
            reason=(
                f"{len(un_escalated_critical)} CRITICAL severity alerts were closed without supervisory or Tier-2 escalation. "
                f"Standard operating procedure requires critical threats to have mandatory supervisory escalation."
            ),
            evidence_summary=f"{len(un_escalated_critical)} critical alerts lacked escalation timestamps and escalation records.",
            observed_value_json=json.dumps({"unescalated_critical_count": len(un_escalated_critical)}),
            expected_value_json=json.dumps({"mandatory_escalation_rate": "100.0%"}),
            metric_values_json=json.dumps({
                "un_escalated_critical_count": len(un_escalated_critical),
                "total_critical_count": len([a for a in critical_alerts if a.severity == 'CRITICAL'])
            }),
            baseline_json=json.dumps({
                "expected_escalation_rate_critical": "100.0%",
                "observed_escalation_rate": f"{round((1 - len(un_escalated_critical) / max(len(critical_alerts), 1)) * 100, 1)}%"
            }),
            recommended_review_area="Inspect Incident Response Playbook section on mandatory escalation protocols for critical assets.",
            sample_size=len(un_escalated_critical),
            status="NEW"
        )
        evidence_links = [
            FindingEvidenceLink(
                finding_id=fnd_id,
                entity_id=entity_id,
                record_type="ALERT",
                record_id=a.alert_id,
                relevance_note=f"Category '{a.category}', closed without escalation flag"
            )
            for a in un_escalated_critical[:20]
        ]
        findings_with_evidence.append((finding, evidence_links))

    # 3. Repeated Alerts Without Remediation
    repeat_query = db.query(
        Alert.asset_id,
        Alert.category,
        func.count(Alert.id).label("cnt")
    ).filter(
        Alert.entity_id == entity_id,
        Alert.asset_id.isnot(None)
    ).group_by(Alert.asset_id, Alert.category).having(func.count(Alert.id) >= 10).all()

    for asset_id, category, count in repeat_query:
        alerts_for_asset = db.query(Alert).filter(
            Alert.entity_id == entity_id,
            Alert.asset_id == asset_id,
            Alert.category == category
        ).all()
        remediated_count = sum(1 for a in alerts_for_asset if a.remediation_recorded)
        if remediated_count == 0 or (remediated_count / count) < 0.15:
            fnd_id = f"FND-GAP-REPEAT-{uuid.uuid4().hex[:8].upper()}"
            finding = Finding(
                finding_id=fnd_id,
                run_id=run_id,
                entity_id=entity_id,
                assessment_period_id=assessment_period_id,
                finding_type="REPEATED_ALERTS_WITHOUT_REMEDIATION",
                capability_dimension="INCIDENT_RESPONSE",
                category="EXECUTION_GAP",
                severity="HIGH",
                confidence=0.90,
                reason=(
                    f"Asset '{asset_id}' generated {count} repeated '{category}' alerts, "
                    f"yet remediation was documented in only {remediated_count} instances ({round(remediated_count/count*100, 1)}%). "
                    f"Indicates recurrence of known vulnerabilities without preventive resolution."
                ),
                evidence_summary=f"{count} persistent alerts observed on target host without permanent fix.",
                observed_value_json=json.dumps({"repeat_count": count, "remediated_count": remediated_count}),
                expected_value_json=json.dumps({"remediation_threshold": ">= 80.0%", "max_allowed_repeat_unremediated": 5}),
                metric_values_json=json.dumps({
                    "asset_id": asset_id,
                    "category": category,
                    "repeat_alert_count": count,
                    "remediated_count": remediated_count
                }),
                baseline_json=json.dumps({
                    "max_tolerated_repeat_unremediated": 5,
                    "remediation_target_rate": "80.0%"
                }),
                recommended_review_area="Request root-cause analysis and remediation change ticket for target host.",
                sample_size=count,
                status="NEW"
            )
            evidence_links = [
                FindingEvidenceLink(
                    finding_id=fnd_id,
                    entity_id=entity_id,
                    record_type="ALERT",
                    record_id=a.alert_id,
                    relevance_note=f"Repeat alert on {asset_id} at {a.alert_timestamp}"
                )
                for a in alerts_for_asset[:15]
            ]
            findings_with_evidence.append((finding, evidence_links))

    # 4. Metric Optimization / Investigation Evidence Absence Pattern
    total_alerts = db.query(Alert).filter(Alert.entity_id == entity_id).count()
    if total_alerts >= 50:
        no_evidence_count = db.query(Alert).filter(
            Alert.entity_id == entity_id,
            Alert.evidence_present.is_(False)
        ).count()
        pct_no_evidence = (no_evidence_count / total_alerts) * 100.0

        if pct_no_evidence >= 75.0:
            fnd_id = f"FND-GAP-WEAKEV-{uuid.uuid4().hex[:8].upper()}"
            finding = Finding(
                finding_id=fnd_id,
                run_id=run_id,
                entity_id=entity_id,
                assessment_period_id=assessment_period_id,
                finding_type="METRIC_OPTIMIZATION_WEAK_EVIDENCE",
                capability_dimension="INVESTIGATION",
                category="EXECUTION_GAP",
                severity="CRITICAL",
                confidence=0.94,
                reason=(
                    f"{no_evidence_count} out of {total_alerts} alerts ({pct_no_evidence:.1f}%) were closed with NO attached evidence "
                    f"or documented investigation findings. Suggests superficial ticket closure aimed at meeting SLA velocity metrics."
                ),
                evidence_summary=f"{pct_no_evidence:.1f}% evidence deficit across general operational queue.",
                observed_value_json=json.dumps({"missing_evidence_pct": round(pct_no_evidence, 1)}),
                expected_value_json=json.dumps({"peer_baseline_evidence_rate": ">= 80.0%"}),
                metric_values_json=json.dumps({
                    "total_alerts": total_alerts,
                    "no_evidence_count": no_evidence_count,
                    "percentage_missing_evidence": round(pct_no_evidence, 1)
                }),
                baseline_json=json.dumps({
                    "acceptable_missing_evidence_max_pct": 20.0,
                    "peer_baseline_evidence_rate": "82.5%"
                }),
                recommended_review_area="Audit analyst triage checklists and verify if ticket closure requires mandatory PCAP or log attachments.",
                sample_size=no_evidence_count,
                status="NEW"
            )
            sample_no_ev = db.query(Alert).filter(
                Alert.entity_id == entity_id,
                Alert.evidence_present.is_(False)
            ).limit(20).all()

            evidence_links = [
                FindingEvidenceLink(
                    finding_id=fnd_id,
                    entity_id=entity_id,
                    record_type="ALERT",
                    record_id=a.alert_id,
                    relevance_note="Closed with evidence_present=False"
                )
                for a in sample_no_ev
            ]
            findings_with_evidence.append((finding, evidence_links))

    # 5. Template / Repetitive Boilerplate Investigation Notes Pattern
    cases = db.query(Case).filter(Case.entity_id == entity_id).all()
    if len(cases) >= 20:
        notes = [c.closure_reason.strip() for c in cases if c.closure_reason and len(c.closure_reason.strip()) > 5]
        if notes:
            from collections import Counter
            counts = Counter(notes)
            most_common_text, top_count = counts.most_common(1)[0]
            pct_boilerplate = (top_count / len(notes)) * 100.0

            if pct_boilerplate >= 60.0:
                fnd_id = f"FND-GAP-TEMPLATE-{uuid.uuid4().hex[:8].upper()}"
                finding = Finding(
                    finding_id=fnd_id,
                    run_id=run_id,
                    entity_id=entity_id,
                    assessment_period_id=assessment_period_id,
                    finding_type="TEMPLATE_INVESTIGATION_PATTERN",
                    capability_dimension="OPERATIONAL_DISCIPLINE",
                    category="EXECUTION_GAP",
                    severity="HIGH",
                    confidence=0.91,
                    reason=(
                        f"{top_count} out of {len(notes)} case closures ({pct_boilerplate:.1f}%) utilized identical boilerplate text: "
                        f"\"{most_common_text}\". Demonstrates repetitive mechanical dispositioning without individualized investigation."
                    ),
                    evidence_summary=f"{pct_boilerplate:.1f}% boilerplate repetition in case management closure reasons.",
                    observed_value_json=json.dumps({"boilerplate_repetition_pct": round(pct_boilerplate, 1), "text_sample": most_common_text}),
                    expected_value_json=json.dumps({"max_identical_closure_pct": "15.0%"}),
                    metric_values_json=json.dumps({
                        "identical_closures_count": top_count,
                        "total_evaluated_cases": len(notes),
                        "repetition_percentage": round(pct_boilerplate, 1)
                    }),
                    baseline_json=json.dumps({"acceptable_repetition_max": "15.0%"}),
                    recommended_review_area="Review analyst quality assurance and mandate structured root-cause classifications.",
                    sample_size=top_count,
                    status="NEW"
                )
                matched_cases = [c for c in cases if c.closure_reason and c.closure_reason.strip() == most_common_text]
                evidence_links = [
                    FindingEvidenceLink(
                        finding_id=fnd_id,
                        entity_id=entity_id,
                        record_type="CASE",
                        record_id=c.case_id,
                        relevance_note=f"Boilerplate closure text: '{most_common_text}'"
                    )
                    for c in matched_cases[:20]
                ]
                findings_with_evidence.append((finding, evidence_links))

    return findings_with_evidence
