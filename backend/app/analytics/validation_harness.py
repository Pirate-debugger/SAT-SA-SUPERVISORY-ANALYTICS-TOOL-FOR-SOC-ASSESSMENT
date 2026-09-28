from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.finding import Finding


EXPERT_VALIDATION_GROUND_TRUTH = [
    {
        "entity_id": "CSE-BANK-02",
        "expected_type": "CRITICAL_ALERT_RAPID_CLOSURE",
        "expected_category": "EXECUTION_GAP",
        "expected_severity": "CRITICAL",
        "expected_dimension": "SECURITY_OPERATIONS",
        "expert_label": "High-severity alerts closed in 2-5 mins with template comments without triage",
        "planted_scenario_id": "SCENARIO_1_RAPID_CLOSURE"
    },
    {
        "entity_id": "CSE-POWER-01",
        "expected_type": "CRITICAL_ALERTS_WITHOUT_ESCALATION",
        "expected_category": "EXECUTION_GAP",
        "expected_severity": "HIGH",
        "expected_dimension": "ESCALATION",
        "expert_label": "Critical SCADA alerts closed directly at Tier-1 without supervisory escalation",
        "planted_scenario_id": "SCENARIO_2_UNESCALATED_CRITICAL"
    },
    {
        "entity_id": "CSE-HEALTH-03",
        "expected_type": "REPEATED_ALERTS_WITHOUT_REMEDIATION",
        "expected_category": "EXECUTION_GAP",
        "expected_severity": "HIGH",
        "expected_dimension": "INCIDENT_RESPONSE",
        "expert_label": "Asset generates 35+ repeated alerts with zero documented remediation or root-cause",
        "planted_scenario_id": "SCENARIO_3_REPEAT_UNREMEDIATED"
    },
    {
        "entity_id": "CSE-TRANS-04",
        "expected_type": "METRIC_OPTIMIZATION_WEAK_EVIDENCE",
        "expected_category": "EXECUTION_GAP",
        "expected_severity": "CRITICAL",
        "expected_dimension": "INVESTIGATION",
        "expert_label": "General queue has 80%+ missing evidence rate indicating SLA velocity metrics gaming",
        "planted_scenario_id": "SCENARIO_4_WEAK_INVESTIGATION"
    },
    {
        "entity_id": "CSE-TELECOM-05",
        "expected_type": "CRITICAL_ASSET_TELEMETRY_SILENCE",
        "expected_category": "NEGATIVE_SPACE",
        "expected_severity": "CRITICAL",
        "expected_dimension": "CYBER_RESILIENCE",
        "expert_label": "Declared 140 critical core routers but only 10 ever report any telemetry (>90% gap)",
        "planted_scenario_id": "SCENARIO_5_ASSET_SILENCE"
    },
    {
        "entity_id": "CSE-TELECOM-05",
        "expected_type": "EXPECTED_ALERT_CATEGORY_ABSENT",
        "expected_category": "NEGATIVE_SPACE",
        "expected_severity": "HIGH",
        "expected_dimension": "THREAT_DETECTION",
        "expert_label": "Expected core threat signatures (Ransomware, Data Exfiltration) completely absent",
        "planted_scenario_id": "SCENARIO_6_ABSENT_CATEGORY"
    }
]


def run_expert_validation_benchmark(db: Session, run_id: str) -> Dict[str, Any]:
    """
    Evaluates system analytical accuracy against expert-labelled ground truth cases.
    Computes Precision, Recall, False Positive Rate, and Evidence Coverage.
    """
    detected_findings = db.query(Finding).filter(Finding.run_id == run_id).all()

    # Track matches
    true_positives = 0
    matched_scenarios = set()
    scenario_details = []

    for gt in EXPERT_VALIDATION_GROUND_TRUTH:
        matched = False
        matching_finding = None

        for df in detected_findings:
            if df.entity_id == gt["entity_id"] and df.finding_type == gt["expected_type"]:
                matched = True
                matching_finding = df
                break

        if matched and matching_finding:
            true_positives += 1
            matched_scenarios.add(gt["planted_scenario_id"])
            scenario_details.append({
                "scenario_id": gt["planted_scenario_id"],
                "entity_id": gt["entity_id"],
                "finding_type": gt["expected_type"],
                "status": "DETECTED_CORRECTLY",
                "confidence": matching_finding.confidence,
                "evidence_sample_size": matching_finding.sample_size,
                "expert_label": gt["expert_label"]
            })
        else:
            scenario_details.append({
                "scenario_id": gt["planted_scenario_id"],
                "entity_id": gt["entity_id"],
                "finding_type": gt["expected_type"],
                "status": "MISSED_FALSE_NEGATIVE",
                "confidence": 0.0,
                "evidence_sample_size": 0,
                "expert_label": gt["expert_label"]
            })

    total_ground_truth = len(EXPERT_VALIDATION_GROUND_TRUTH)
    total_detected = len(detected_findings)

    recall = (true_positives / total_ground_truth) if total_ground_truth > 0 else 0.0
    precision = (true_positives / total_detected) if total_detected > 0 else 0.0
    # False discovery / unlabelled findings count
    unlabelled_detections = max(0, total_detected - true_positives)
    fpr = (unlabelled_detections / max(total_detected, 1))

    # Evidence coverage: percentage of findings that have concrete linked records
    findings_with_evidence = sum(1 for df in detected_findings if len(df.evidence_links) > 0)
    evidence_coverage = (findings_with_evidence / max(total_detected, 1)) * 100.0

    return {
        "benchmark_title": "SYNTHETIC EXPERT-LABELLED VALIDATION HARNESS",
        "disclaimer": "SYNTHETIC BENCHMARK EVALUATION ONLY — NOT REAL NCIIPC/GOVERNMENT DATA",
        "run_id": run_id,
        "metrics": {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(2 * (precision * recall) / max(precision + recall, 0.001), 3),
            "false_positive_rate": round(fpr, 3),
            "evidence_coverage_pct": round(evidence_coverage, 1),
            "total_ground_truth_cases": total_ground_truth,
            "detected_true_positives": true_positives,
            "total_system_findings": total_detected
        },
        "scenarios": scenario_details
    }
