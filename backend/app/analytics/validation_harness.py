from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.finding import Finding
from app.models.audit import ExpertReviewLabel


# Mode A: Synthetic Planted Ground Truth Scenarios (Positive and Negative Controls)
SYNTHETIC_GROUND_TRUTH_SCENARIOS = [
    # Positive Ground Truth (Expected Detections)
    {
        "scenario_id": "SCENARIO_1_RAPID_CLOSURE",
        "entity_id": "CSE-BANK-02",
        "expected_type": "CRITICAL_ALERT_RAPID_CLOSURE",
        "ground_truth_label": "POSITIVE",
        "expert_rationale": "High-severity alerts closed in 2-5 mins with template comments without substantive triage"
    },
    {
        "scenario_id": "SCENARIO_2_UNESCALATED_CRITICAL",
        "entity_id": "CSE-POWER-01",
        "expected_type": "CRITICAL_ALERTS_WITHOUT_ESCALATION",
        "ground_truth_label": "POSITIVE",
        "expert_rationale": "Critical SCADA alerts closed directly at Tier-1 without mandatory supervisory escalation"
    },
    {
        "scenario_id": "SCENARIO_3_REPEAT_UNREMEDIATED",
        "entity_id": "CSE-HEALTH-03",
        "expected_type": "REPEATED_ALERTS_WITHOUT_REMEDIATION",
        "ground_truth_label": "POSITIVE",
        "expert_rationale": "Asset generates 35+ repeated alerts with zero documented remediation or root-cause"
    },
    {
        "scenario_id": "SCENARIO_4_WEAK_INVESTIGATION",
        "entity_id": "CSE-TRANS-04",
        "expected_type": "METRIC_OPTIMIZATION_WEAK_EVIDENCE",
        "ground_truth_label": "POSITIVE",
        "expert_rationale": "General queue has 80%+ missing evidence rate indicating SLA velocity metrics gaming"
    },
    {
        "scenario_id": "SCENARIO_5_ASSET_SILENCE",
        "entity_id": "CSE-TELECOM-05",
        "expected_type": "CRITICAL_ASSET_TELEMETRY_SILENCE",
        "ground_truth_label": "POSITIVE",
        "expert_rationale": "Declared 140 critical core routers but only 10 ever report any telemetry (>90% gap)"
    },
    {
        "scenario_id": "SCENARIO_6_ABSENT_CATEGORY",
        "entity_id": "CSE-TELECOM-05",
        "expected_type": "EXPECTED_ALERT_CATEGORY_ABSENT",
        "ground_truth_label": "POSITIVE",
        "expert_rationale": "Expected core threat signatures (Ransomware, Data Exfiltration) completely absent"
    },
    # Negative Ground Truth Controls (Should NOT trigger these findings)
    {
        "scenario_id": "NEGATIVE_CONTROL_1_POWER_NO_RAPID_CLOSURE",
        "entity_id": "CSE-POWER-01",
        "expected_type": "CRITICAL_ALERT_RAPID_CLOSURE",
        "ground_truth_label": "NEGATIVE",
        "expert_rationale": "CSE-POWER-01 exhibits normal multi-hour investigation durations; should not trigger rapid closure"
    },
    {
        "scenario_id": "NEGATIVE_CONTROL_2_BANK_NO_ASSET_SILENCE",
        "entity_id": "CSE-BANK-02",
        "expected_type": "CRITICAL_ASSET_TELEMETRY_SILENCE",
        "ground_truth_label": "NEGATIVE",
        "expert_rationale": "CSE-BANK-02 has active telemetry across declared assets; should not trigger asset silence"
    }
]


def run_synthetic_ground_truth_benchmark(db: Session, run_id: str) -> Dict[str, Any]:
    """
    Mode A: Internal Synthetic Ground-Truth Benchmark (Section 21A).
    Measures TP, FP, TN, FN, Precision, Recall, F1.
    Computes FPR strictly using actual negative ground-truth controls (FPR = FP / (FP + TN)).
    Never misuses unlabelled detections as False Positive Rate.
    """
    detected_findings = db.query(Finding).filter(Finding.run_id == run_id).all()

    tp = 0
    fn = 0
    fp = 0
    tn = 0
    scenario_results = []

    for item in SYNTHETIC_GROUND_TRUTH_SCENARIOS:
        is_detected = any(
            df.entity_id == item["entity_id"] and df.finding_type == item["expected_type"]
            for df in detected_findings
        )

        if item["ground_truth_label"] == "POSITIVE":
            if is_detected:
                tp += 1
                status = "TRUE_POSITIVE_DETECTED"
            else:
                fn += 1
                status = "FALSE_NEGATIVE_MISSED"
        else:  # NEGATIVE control
            if is_detected:
                fp += 1
                status = "FALSE_POSITIVE_FLAGGED"
            else:
                tn += 1
                status = "TRUE_NEGATIVE_CORRECTLY_IGNORED"

        scenario_results.append({
            "scenario_id": item["scenario_id"],
            "entity_id": item["entity_id"],
            "expected_type": item["expected_type"],
            "ground_truth_label": item["ground_truth_label"],
            "result_status": status,
            "expert_rationale": item["expert_rationale"]
        })

    positives = tp + fn
    negatives = fp + tn

    precision = (tp / max(tp + fp, 1)) if (tp + fp) > 0 else 0.0
    recall = (tp / max(positives, 1)) if positives > 0 else 0.0
    f1 = (2 * precision * recall / max(precision + recall, 0.0001)) if (precision + recall) > 0 else 0.0

    # True statistical FPR = FP / (FP + TN) on defined negative controls
    fpr = (fp / max(negatives, 1)) if negatives > 0 else 0.0

    # Evidence coverage
    findings_with_evidence = sum(1 for df in detected_findings if len(df.evidence_links) > 0)
    evidence_coverage = (findings_with_evidence / max(len(detected_findings), 1)) * 100.0

    return {
        "validation_mode": "SYNTHETIC_GROUND_TRUTH_BENCHMARK",
        "disclaimer": "DEMO / SYNTHETIC DATA BENCHMARK — NOT FOR OPERATIONAL USE",
        "run_id": run_id,
        "confusion_matrix": {
            "true_positives": tp,
            "false_negatives": fn,
            "true_negatives": tn,
            "false_positives": fp
        },
        "performance_metrics": {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3),
            "false_positive_rate": round(fpr, 3),
            "evidence_coverage_pct": round(evidence_coverage, 1),
            "total_system_findings": len(detected_findings),
            "unlabelled_exploratory_findings": max(0, len(detected_findings) - tp)
        },
        "scenarios": scenario_results
    }


def run_expert_validation_benchmark(db: Session, run_id: str) -> Dict[str, Any]:
    """Compatibility wrapper returning Mode A synthetic benchmark."""
    return run_synthetic_ground_truth_benchmark(db, run_id)


def evaluate_expert_review_mode(db: Session, run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Mode B: Expert Review Mode (Section 21B).
    Compares real human supervisor expert labels with system findings.
    Only computes calibration when actual expert annotations exist.
    """
    labels = db.query(ExpertReviewLabel).all()
    if not labels:
        return {
            "validation_mode": "HUMAN_EXPERT_REVIEW_MODE",
            "status": "AWAITING_EXPERT_LABELS",
            "sufficient_expert_data": False,
            "message": (
                "No human cybersecurity expert labels recorded yet. "
                "System does not claim expert validation until authorized expert annotations are submitted."
            ),
            "total_expert_labels": 0,
            "agreement_rate_pct": None,
            "expert_labels": []
        }


    agreed_count = 0
    detailed_comparisons = []

    for el in labels:
        # Check system finding matching target_id
        fnd = db.query(Finding).filter(Finding.finding_id == el.target_id).first()
        is_agreed = False
        system_finding_type = None

        if fnd:
            system_finding_type = fnd.finding_type
            if el.expert_label in ["TRUE_POSITIVE", "CONFIRMED_GAP"]:
                is_agreed = True
                agreed_count += 1
            elif el.expert_label in ["FALSE_POSITIVE", "BENIGN_ANOMALY"]:
                is_agreed = False
        else:
            # Finding not detected by system
            if el.expert_label in ["FALSE_POSITIVE", "BENIGN_ANOMALY", "INSUFFICIENT_EVIDENCE"]:
                is_agreed = True
                agreed_count += 1

        detailed_comparisons.append({
            "target_id": el.target_id,
            "target_type": el.target_type,
            "entity_id": el.entity_id,
            "expert_label": el.expert_label,
            "reviewer_name": el.reviewer_name,
            "expert_severity": el.severity,
            "system_detected": fnd is not None,
            "system_finding_type": system_finding_type,
            "agreement": is_agreed,
            "notes": el.evidence_notes
        })

    agreement_pct = round((agreed_count / max(len(labels), 1)) * 100.0, 1)

    return {
        "validation_mode": "HUMAN_EXPERT_REVIEW_MODE",
        "status": "VALIDATED_WITH_EXPERT_LABELS",
        "sufficient_expert_data": len(labels) >= 5,
        "total_expert_labels": len(labels),
        "agreement_count": agreed_count,
        "agreement_rate_pct": agreement_pct,
        "comparisons": detailed_comparisons
    }

